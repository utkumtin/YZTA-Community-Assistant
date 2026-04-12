"""
Feature Request Servisi — Akademi Topluluk Asistanı

AMAÇ
----
`/cemilimyapar` komutunun tüm iş mantığını yöneten servis katmanı.
Slack SDK'ya doğrudan erişimi yoktur; manager'lar handler katmanından inject edilir.

İŞ AKIŞLARI
-----------
  submit_request()          → Haftalık hak kontrolü → embed → benzerlik kontrolü → fraud → kaydet
  update_request()          → Mevcut kaydı yeni vektörle güncelle (düzenleme akışı)
  check_weekly_quota()      → Bu hafta kaç submit hakkı kaldı?
  find_similar_this_week()  → Bu haftaki kayıtlarla cosine similarity karşılaştırması
  detect_fraud()            → Farklı kullanıcılardan gelen benzer vektörleri tespit et
  run_clustering_pipeline() → status=embedded → L2 norm → UMAP → HDBSCAN → label → DB yaz
  generate_admin_report()   → Kümelenmiş verilerden Groq ile Türkçe rapor üret

BAĞIMLILIKLAR
-------------
  VectorClient    → Embedding (sentence-transformers)
  GroqClient      → Cluster label ve rapor üretimi (LLM)
  DatabaseManager → Async session yönetimi

DÖNÜŞ TİPLERİ (submit_request)
--------------------------------
  {"status": "created",         "request_id": "FRQ-..."}
  {"status": "similar_found",   "existing_id": "FRQ-...", "existing_text": "..."}
  {"status": "quota_exceeded",  "used": 2, "max": 2}
"""

import logging
import numpy as np
from datetime import datetime
from typing import Any

from packages.database.manager import DatabaseManager
from packages.database.repository.feature_request import (
    FeatureClusterLabelRepository,
    FeatureRequestRepository,
)
from packages.database.models.feature_request import FeatureRequest, FeatureClusterLabel
from packages.vector import VectorClient, VectorClientError
from packages.clients.groq import GroqClient

import umap
import hdbscan


# Constants

WEEKLY_QUOTA = 2  # Kullanıcı başına haftalık maksimum submit sayısı
SIMILARITY_THRESHOLD = 0.85  # Bu eşiğin üstündeki cosine similarity "benzer" sayılır
FRAUD_THRESHOLD = 0.90  # Bu eşiğin üstündeki cross-user similarity "fraud" uyarısı
FRAUD_WINDOW_DAYS = 7  # Fraud tespiti için geriye bakılan gün sayısı
UMAP_N_COMPONENTS = 10  # UMAP çıktı boyutu (768 → 10; HDBSCAN için yeterli)
HDBSCAN_MIN_CLUSTER = 3  # HDBSCAN min_cluster_size


class FeatureRequestService:
    """
    `/cemilimyapar` komutunun iş mantığını yöneten servis sınıfı.

    Tüm infrastructure client'larını constructor'da oluşturur.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger("feature_request_service.FeatureRequestService")
        self.vector_client = VectorClient()
        self.groq_client = GroqClient()
        self.db = DatabaseManager()

    # SUBMIT AKIŞI

    async def submit_request(self, user_id: str, raw_text: str) -> dict[str, Any]:
        """
        Ana submit akışı. Sırasıyla şunları yapar:

        1. Haftalık hak kontrolü → dolmuşsa `quota_exceeded` döndür.
        2. Metni embed et.
        3. Bu haftaki kayıtlarla benzerlik kontrolü → benzer varsa `similar_found` döndür.
        4. Fraud tespiti.
        5. DB'ye kaydet → `created` döndür.

        Args:
            user_id:  Talebi gönderen kullanıcının DB id'si (users.id).
            raw_text: Modal'dan gelen ham talep metni.

        Returns:
            status="created"       → {"status": "created", "request_id": "FRQ-..."}
            status="similar_found" → {"status": "similar_found", "existing_id": ..., "existing_text": ...}
            status="quota_exceeded"→ {"status": "quota_exceeded", "used": N, "max": N}
        """
        async with self.db.session_scope() as session:
            repo = FeatureRequestRepository(session)

            # 1. Haftalık hak kontrolü
            used = await self.check_weekly_quota(user_id, repo)
            if used >= WEEKLY_QUOTA:
                self.logger.info(
                    f"Haftalık kota aşıldı.", extra={"user_id": user_id, "used": used}
                )
                return {"status": "quota_exceeded", "used": used, "max": WEEKLY_QUOTA}

            # 2. Embed
            try:
                vector = self.vector_client.embed(raw_text)
            except Exception as exc:
                self.logger.error(f"Embed hatası: {exc}", exc_info=True)
                # Embedding başarısız olsa dahi kaydı `embedding_failed` statusuyla ekle
                failed_req = FeatureRequest(
                    user_id=user_id,
                    request_raw=raw_text,
                    status="embedding_failed",
                )
                session.add(failed_req)
                await session.flush()
                return {"status": "created", "request_id": failed_req.id}

            # 3. Benzerlik kontrolü
            similar = await self.find_similar_this_week(user_id, vector, repo)
            if similar is not None:
                self.logger.info(
                    f"Benzer kayıt bulundu.",
                    extra={"user_id": user_id, "similar_id": similar.id},
                )
                return {
                    "status": "similar_found",
                    "existing_id": similar.id,
                    "existing_text": similar.request_raw,
                }

            # 4. Fraud tespiti
            fraud_score = await self.detect_fraud(vector, user_id, repo)

            # 5. Kaydet
            new_request = FeatureRequest(
                user_id=user_id,
                request_raw=raw_text,
                request_embedded=vector.tolist(),
                status="embedded",
                fraud_score=fraud_score,
            )
            session.add(new_request)
            await session.flush()

            self.logger.info(
                f"Yeni feature request kaydedildi.",
                extra={"user_id": user_id, "request_id": new_request.id},
            )
            return {"status": "created", "request_id": new_request.id}

    async def update_request(self, request_id: str, new_text: str) -> dict[str, Any]:
        """
        Mevcut bir talebi günceller (düzenleme akışı — 'Evet, düzenleyeyim' butonu).

        Yeni metin için yeni bir embedding üretir, kaydı günceller ve
        status'u 'embedded' olarak sıfırlar (clustering kuyruğuna geri girer).

        Args:
            request_id: Güncellenecek FeatureRequest'in id'si.
            new_text:   Düzenleme modal'ından gelen yeni ham metin.

        Returns:
            {"status": "updated", "request_id": "FRQ-..."}
            {"status": "not_found"}
        """
        async with self.db.session_scope() as session:
            repo = FeatureRequestRepository(session)
            request = await repo.get(request_id)

            if request is None:
                self.logger.warning(
                    f"Güncellenecek kayıt bulunamadı.", extra={"request_id": request_id}
                )
                return {"status": "not_found"}

            try:
                new_vector = self.vector_client.embed(new_text)
                new_embedded = new_vector.tolist()
            except Exception as exc:
                self.logger.error(f"Güncelleme embed hatası: {exc}", exc_info=True)
                new_embedded = None

            request.request_raw = new_text
            request.request_embedded = new_embedded
            request.status = "embedded" if new_embedded else "embedding_failed"
            request.cluster_id = None  # Önceki cluster atamasını sıfırla
            await repo.update(request)

            self.logger.info(
                f"Feature request güncellendi.", extra={"request_id": request_id}
            )
            return {"status": "updated", "request_id": request_id}

    # ==========================================================================
    # YARDIMCI METODLAR
    # ==========================================================================

    async def check_weekly_quota(
        self,
        user_id: str,
        repo: FeatureRequestRepository | None = None,
    ) -> int:
        """
        Kullanıcının bu hafta kaç submit kullandığını döndürür.

        Args:
            user_id: Sorgulanacak kullanıcının DB id'si.
            repo:    Opsiyonel — halihazırda açık bir session varsa inject edilir.
                     None ise yeni session açılır.

        Returns:
            Kullanılan submit sayısı (int). WEEKLY_QUOTA ile karşılaştırılmalı.
        """
        if repo is not None:
            records = await repo.list_by_user_this_week(user_id)
            return len(records)

        async with self.db.session_scope() as session:
            records = await FeatureRequestRepository(session).list_by_user_this_week(
                user_id
            )
            return len(records)

    async def find_similar_this_week(
        self,
        user_id: str,
        new_vector: np.ndarray,
        repo: FeatureRequestRepository | None = None,
    ):
        """
        Kullanıcının bu haftaki kayıtları arasında new_vector'e çok benzer
        (cosine similarity > SIMILARITY_THRESHOLD) bir kayıt arar.

        Args:
            user_id:    Arama yapılacak kullanıcının DB id'si.
            new_vector: Yeni talebin embedding vektörü.
            repo:       Opsiyonel inject edilmiş repository.

        Returns:
            Benzer kayıt bulunursa FeatureRequest nesnesi, yoksa None.
        """
        if repo is not None:
            existing = await repo.list_embedded_vectors(user_id)
        else:
            async with self.db.session_scope() as session:
                existing = await FeatureRequestRepository(
                    session
                ).list_embedded_vectors(user_id)

        for record in existing:
            if record.request_embedded is None:
                continue
            try:
                existing_vec = np.array(record.request_embedded, dtype=np.float32)
                similarity = self.vector_client.cosine_similarity(
                    new_vector, existing_vec
                )
                if similarity > SIMILARITY_THRESHOLD:
                    self.logger.debug(
                        f"Benzer kayıt bulundu (sim={similarity:.4f}).",
                        extra={"existing_id": record.id},
                    )
                    return record
            except Exception as exc:
                self.logger.warning(
                    f"Benzerlik hesaplama hatası (atlanıyor): {exc}",
                    extra={"record_id": record.id},
                )
                continue

        return None

    async def detect_fraud(
        self,
        new_vector: np.ndarray,
        user_id: str,
        repo: FeatureRequestRepository | None = None,
    ) -> float:
        """
        Farklı kullanıcılardan gelen son 7 günlük talep vektörleriyle
        new_vector'ü karşılaştırır ve bir fraud_score üretir.

        Fraud score = benzer kayıt sayısı / toplam karşılaştırılan kayıt sayısı.
        Eşiğin üstünde benzerlik gösteren kayıt yoksa 0.0 döner.

        Args:
            new_vector: Değerlendirilecek vektör.
            user_id:    Kendi kayıtlarını eşleşme listesinden çıkarmak için.
            repo:       Opsiyonel inject edilmiş repository.

        Returns:
            0.0–1.0 arası fraud skoru.
        """
        # Son 7 günlük embedded kaydı çek (kendi kayıtları hariç)
        if repo is not None:
            all_embedded = await repo.list_by_status("embedded")
        else:
            async with self.db.session_scope() as session:
                all_embedded = await FeatureRequestRepository(session).list_by_status(
                    "embedded"
                )

        others = [
            r for r in all_embedded if r.user_id != user_id and r.request_embedded
        ]
        if not others:
            return 0.0

        similar_count = 0
        for record in others:
            try:
                other_vec = np.array(record.request_embedded, dtype=np.float32)
                similarity = self.vector_client.cosine_similarity(new_vector, other_vec)
                if similarity >= FRAUD_THRESHOLD:
                    similar_count += 1
            except Exception:
                continue

        score = similar_count / len(others)
        if score > 0:
            self.logger.warning(
                f"Fraud tespit edildi (score={score:.3f}).",
                extra={"user_id": user_id, "similar_count": similar_count},
            )
        return round(score, 4)

    # ==========================================================================
    # CLUSTERING PIPELINE
    # ==========================================================================

    async def run_clustering_pipeline(self) -> dict[str, Any]:
        """
        status='embedded' olan tüm kayıtları kümeleme pipeline'ından geçirir.

        Pipeline sırası:
          1. status='embedded' kayıtları çek
          2. BLOB → numpy (N, 768)
          3. L2 normalizasyon
          4. UMAP boyut indirgeme (768 → UMAP_N_COMPONENTS)
          5. HDBSCAN kümeleme
          6. cluster_id'leri DB'ye yaz (status → 'clustered' / 'clustering_failed')
          7. Yeni cluster'lar için Groq label üret → feature_cluster_labels

        Returns:
            {
              "clustered": N,      # Başarıyla atanan kayıt sayısı
              "noise": M,          # Kümeye atanamayan (HDBSCAN -1) kayıt sayısı
              "new_labels": K,     # Bu çalıştırmada üretilen yeni label sayısı
            }
        """
        async with self.db.session_scope() as session:
            fr_repo = FeatureRequestRepository(session)
            fcl_repo = FeatureClusterLabelRepository(session)

            embedded = await fr_repo.list_by_status("embedded")
            if not embedded:
                self.logger.info("Kümelenecek kayıt yok.")
                return {"clustered": 0, "noise": 0, "new_labels": 0}

            # --- Vektör matrisini oluştur ---
            vectors = []
            valid_ids = []
            for record in embedded:
                if record.request_embedded is None:
                    continue
                try:
                    vec = np.array(record.request_embedded, dtype=np.float32)
                    vectors.append(vec)
                    valid_ids.append(record.id)
                except Exception as exc:
                    self.logger.warning(
                        f"BLOB okuma hatası, atlanıyor: {exc}",
                        extra={"record_id": record.id},
                    )

            if len(vectors) < HDBSCAN_MIN_CLUSTER:
                self.logger.info(
                    f"Kümeleme için yeterli kayıt yok "
                    f"(mevcut={len(vectors)}, min={HDBSCAN_MIN_CLUSTER})."
                )
                return {"clustered": 0, "noise": len(vectors), "new_labels": 0}

            # --- L2 normalizasyon ---
            matrix = np.array(vectors, dtype=np.float32)
            norms = np.linalg.norm(matrix, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1.0, norms)  # sıfır bölme koruması
            matrix = matrix / norms

            # --- UMAP boyut indirgeme ---
            self.logger.info(
                f"UMAP çalışıyor: {matrix.shape} → ({len(vectors)}, {UMAP_N_COMPONENTS})"
            )
            try:
                n_neighbors = min(15, len(vectors) - 1)
                reducer = umap.UMAP(
                    n_components=UMAP_N_COMPONENTS,
                    metric="cosine",
                    n_neighbors=n_neighbors,
                    random_state=42,
                )
                reduced = reducer.fit_transform(matrix)
            except Exception as exc:
                self.logger.error(f"UMAP hatası: {exc}", exc_info=True)
                for req_id in valid_ids:
                    record = await fr_repo.get(req_id)
                    if record:
                        record.status = "clustering_failed"
                await session.flush()
                return {"clustered": 0, "noise": len(valid_ids), "new_labels": 0}

            # --- HDBSCAN kümeleme ---
            self.logger.info("HDBSCAN kümeleme başlatılıyor...")
            try:
                clusterer = hdbscan.HDBSCAN(
                    min_cluster_size=HDBSCAN_MIN_CLUSTER,
                    metric="euclidean",
                    prediction_data=True,
                )
                labels = clusterer.fit_predict(reduced)  # -1 = noise
            except Exception as exc:
                self.logger.error(f"HDBSCAN hatası: {exc}", exc_info=True)
                return {"clustered": 0, "noise": len(valid_ids), "new_labels": 0}

            # --- DB güncelleme ---
            clustered_count = 0
            noise_count = 0
            for req_id, cluster_label in zip(valid_ids, labels):
                if cluster_label == -1:
                    noise_count += 1
                    # Noise kayıtlar cluster_id=NULL, status='embedded' kalır
                    continue
                await fr_repo.update_cluster(req_id, int(cluster_label))
                clustered_count += 1

            # --- Yeni cluster'lar için Groq label üret ---
            unique_clusters = set(int(l) for l in labels if l != -1)
            new_labels_count = 0

            for cid in unique_clusters:
                existing_label = await fcl_repo.get_by_cluster_id(cid)
                if existing_label is not None:
                    continue  # Daha önce üretilmiş, tekrar üretme

                # Bu cluster'a ait örnek talepleri bul
                cluster_indices = [i for i, l in enumerate(labels) if l == cid]
                sample_records = [
                    embedded[i] for i in cluster_indices[:5]
                ]  # En fazla 5 örnek
                sample_texts = [r.request_raw for r in sample_records]

                label_text = await self._generate_cluster_label(cid, sample_texts)

                new_label = FeatureClusterLabel(
                    cluster_id=cid,
                    label=label_text,
                    generated_at=datetime.utcnow(),
                    report_count=0,
                )
                session.add(new_label)
                await session.flush()
                new_labels_count += 1

            self.logger.info(
                f"Clustering pipeline tamamlandı.",
                extra={
                    "clustered": clustered_count,
                    "noise": noise_count,
                    "new_labels": new_labels_count,
                },
            )
            return {
                "clustered": clustered_count,
                "noise": noise_count,
                "new_labels": new_labels_count,
            }

    async def _generate_cluster_label(
        self, cluster_id: int, sample_texts: list[str]
    ) -> str:
        """Verilen örnek talepleri kullanarak Groq'a Türkçe cluster başlığı ürettir."""
        samples_str = "\n".join(f"- {t}" for t in sample_texts)
        system_prompt = (
            "Sen bir topluluk asistanısın. Sana birbirine benzer özellik taleplerinin "
            "örneklerini vereceğim. Bu taleplerin genel temasını özetleyen, "
            "kısa (3-6 kelime), Türkçe ve açıklayıcı bir başlık üret. "
            "Sadece başlığı yaz, başka hiçbir şey yazma."
        )
        user_prompt = (
            f"Cluster #{cluster_id} için örnek talepler:\n{samples_str}\n\nBaşlık:"
        )
        try:
            return await self.groq_client.quick_ask(system_prompt, user_prompt)
        except Exception as exc:
            self.logger.warning(
                f"Label üretimi başarısız (cluster={cluster_id}): {exc}"
            )
            return f"Grup #{cluster_id}"  # Fallback label

    # ==========================================================================
    # ADMIN RAPORU
    # ==========================================================================

    async def generate_admin_report(self) -> str:
        """
        status='clustered' olan kayıtlardan Groq ile Türkçe yönetici raporu üretir.

        Raporlanan kayıtların status'unu 'reported' olarak günceller.

        Returns:
            Türkçe rapor metni (str). Kümelenmiş kayıt yoksa bilgilendirici mesaj.
        """
        async with self.db.session_scope() as session:
            fr_repo = FeatureRequestRepository(session)
            fcl_repo = FeatureClusterLabelRepository(session)

            clustered = await fr_repo.list_by_status("clustered")
            if not clustered:
                return "Bu hafta kümelenmiş özellik talebi bulunamadı."

            # Cluster bazında gruplama
            clusters: dict[int, list] = {}
            for record in clustered:
                cid = record.cluster_id
                if cid is None:
                    continue
                clusters.setdefault(cid, []).append(record)

            # Rapor datasını derle
            cluster_summaries: list[str] = []
            reported_ids: list[str] = []

            for cid, records in sorted(clusters.items()):
                label_record = await fcl_repo.get_by_cluster_id(cid)
                label = label_record.label if label_record else f"Grup #{cid}"
                fraud_flagged = [
                    r
                    for r in records
                    if r.fraud_score and r.fraud_score > FRAUD_THRESHOLD
                ]

                examples = "\n".join(f"  • {r.request_raw[:120]}" for r in records[:3])
                fraud_note = (
                    f"\n  ⚠️ {len(fraud_flagged)} fraud şüpheli kayıt var."
                    if fraud_flagged
                    else ""
                )
                cluster_summaries.append(
                    f"*{label}* ({len(records)} talep)\n{examples}{fraud_note}"
                )
                for r in records:
                    reported_ids.append(r.id)

                # report_count güncelle
                if label_record:
                    await fcl_repo.increment_report_count(cid)

            # Groq ile rapor üret
            report_body = "\n\n---\n\n".join(cluster_summaries)
            system_prompt = (
                "Sen bir topluluk yöneticisi asistanısın. Sana haftalık özellik talebi "
                "kümelerini vereceğim. Her küme için başlık, talep sayısı ve örnekler var. "
                "Bunları tek, akıcı, Türkçe bir yönetici raporu haline getir. "
                "Fraud uyarıları varsa belirt. Markdown kullan."
            )
            user_prompt = (
                f"Toplam {len(clustered)} adet kümelenmiş talep, "
                f"{len(clusters)} farklı tema:\n\n{report_body}"
            )

            try:
                report = await self.groq_client.quick_ask(system_prompt, user_prompt)
            except Exception as exc:
                self.logger.error(f"Rapor üretimi başarısız: {exc}", exc_info=True)
                report = (
                    "Rapor üretilirken yapay zeka servisinde hata oluştu.\n\n"
                    + report_body
                )

            # Raporlanan kayıtların status'unu güncelle
            if reported_ids:
                await fr_repo.mark_reported(reported_ids)

            self.logger.info(
                f"Admin raporu oluşturuldu.",
                extra={
                    "total_requests": len(clustered),
                    "total_clusters": len(clusters),
                },
            )
            return report

    # ==========================================================================
    # CRON YARDIMCILARI MANTIĞI
    # ==========================================================================

    async def _notify_admins(self, message: str) -> None:
        """Sistem uyarılarını slack_admins'e DM atar."""
        from packages.settings import get_settings
        from packages.slack.client import slack_client

        settings = get_settings()

        try:
            for admin_id in settings.slack_admins:
                await slack_client.bot_client.chat_postMessage(
                    channel=admin_id, text=message
                )
        except Exception as exc:
            self.logger.error(f"Admin bildirim hatası: {exc}", exc_info=True)

    async def send_weekly_report(self) -> None:
        """generate_admin_report() çağırıp dönen raporu adminlere DM atar."""
        from packages.settings import get_settings
        from packages.slack.client import slack_client
        from packages.slack.blocks.layouts import Layouts

        try:
            report_text = await self.generate_admin_report()
            blocks = Layouts.feature_request_report(report_text)

            settings = get_settings()
            for admin_id in settings.slack_admins:
                await slack_client.bot_client.chat_postMessage(
                    channel=admin_id,
                    text="Haftalık Özellik Talepleri Raporu",
                    blocks=blocks,
                )

            self.logger.info("Haftalık rapor adminlere iletildi.")
        except Exception as exc:
            self.logger.error(
                f"Haftalık rapor gönderimi başarısız: {exc}", exc_info=True
            )

    async def retry_failed_embeddings(self) -> None:
        """status='embedding_failed' olan kayıtları bulup tekrar embed etmeye çalışır."""
        async with self.db.session_scope() as session:
            repo = FeatureRequestRepository(session)
            failed_records = await repo.list_by_status("embedding_failed")
            if not failed_records:
                return

            success_count = 0
            for record in failed_records:
                try:
                    vector = self.vector_client.embed(record.request_raw)
                    record.request_embedded = vector.tolist()
                    record.status = "embedded"
                    success_count += 1
                except Exception as exc:
                    self.logger.warning(f"Retry embed hatasi (ID:{record.id}): {exc}")

            await session.flush()
            self.logger.info(
                f"Embedding retry bitti: {success_count}/{len(failed_records)} kayıt kurtarıldı."
            )

    async def check_clustering_failed(self) -> None:
        """status='clustering_failed' olan kayıtları kontrol eder ve hâlâ varsa uyarı gönderir."""
        async with self.db.session_scope() as session:
            repo = FeatureRequestRepository(session)
            failed_records = await repo.list_by_status("clustering_failed")

            if failed_records:
                message = (
                    f"🚨 *Clustering Uyarı:* Rapor saati yaklaşmasına rağmen "
                    f"*{len(failed_records)} kayıt* hâlâ kümelenemedi (clustering_failed). "
                    f"Makine öğrenimi pipeline'ını kontrol edin."
                )
                await self._notify_admins(message)
