"""
VectorClient — Akademi Topluluk Asistanı

AMAÇ
----
`paraphrase-multilingual-mpnet-base-v2` modelini sarmalayan, bot genelinde
tek bir örnek çalışan (Singleton) embedding istemcisi.

NE YAPAR
--------
• Tek metin veya metin listesini 768 boyutlu dense vektöre dönüştürür.
• İki vektör arasındaki cosine benzerliğini hesaplar.
• SQLite BLOB ↔ numpy.ndarray dönüşümü sağlar (DB okuma/yazma).

KULLANIM
--------
    from src.infrastructure.clients.vector import VectorClient

    vc = VectorClient()                          # Singleton; model tek kez yüklenir
    vec  = vc.embed("Yeni bir özellik istiyorum")   # ndarray shape=(768,)
    blob = vc.to_bytes(vec)                      # DB'ye yazılacak bytes
    vec2 = vc.from_bytes(blob)                   # DB'den okunmuş bytes → ndarray
    sim  = vc.cosine_similarity(vec, vec2)       # float [0.0, 1.0]

HATA YÖNETİMİ
--------------
• Model yüklenemezse VectorClientError fırlatır.
• Encode işlemi başarısız olursa VectorClientError fırlatır.
• BLOB dönüşümü başarısız olursa VectorClientError fırlatır.

MODEL
-----
  paraphrase-multilingual-mpnet-base-v2
    - 768 boyutlu dense vektör çıktısı
    - 50+ dil desteği (Türkçe dahil)
    - ~420 MB (ilk çalıştırmada HuggingFace'den indirilir, sonrası cache)
"""

import numpy as np
from sentence_transformers import SentenceTransformer

from packages.logger.manager import get_logger

logger = get_logger("vector_client")


class VectorClient(metaclass=SingletonMeta):
    """
    sentence-transformers tabanlı Singleton embedding istemcisi.

    İlk örneklendiğinde modeli yükler (~420 MB, bir kez). Sonraki
    çağrılar aynı yüklü modeli kullanır.
    """

    MODEL_NAME = "paraphrase-multilingual-mpnet-base-v2"
    VECTOR_DIM = 768
    _DTYPE = np.float32

    def __init__(self) -> None:
        try:
            logger.info(f"[>] VectorClient: '{self.MODEL_NAME}' modeli yükleniyor...")
            self._model = SentenceTransformer(self.MODEL_NAME)
            logger.info(
                f"[+] VectorClient hazır. Model: {self.MODEL_NAME}, Boyut: {self.VECTOR_DIM}"
            )
        except Exception as exc:
            raise VectorClientError(
                f"Embedding modeli yüklenemedi ('{self.MODEL_NAME}'): {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Encode
    # ------------------------------------------------------------------

    def embed(self, text: str) -> np.ndarray:
        """
        Tek bir metni 768 boyutlu float32 vektöre dönüştürür.

        Args:
            text: Encode edilecek metin.

        Returns:
            shape=(768,) dtype=float32 ndarray.

        Raises:
            VectorClientError: Encode işlemi başarısız olursa.
        """
        if not text or not text.strip():
            raise VectorClientError("Boş metin encode edilemez.")
        try:
            vector: np.ndarray = self._model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=True,  # cosine sim = dot prod sonrası
            )
            return vector.astype(self._DTYPE)
        except Exception as exc:
            raise VectorClientError(f"Embed işlemi başarısız: {exc}") from exc

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """
        Metin listesini (N, 768) boyutlu matrise dönüştürür.

        Args:
            texts: Encode edilecek metin listesi. Boş liste hata fırlatır.

        Returns:
            shape=(N, 768) dtype=float32 ndarray.

        Raises:
            VectorClientError: Liste boşsa veya encode başarısız olursa.
        """
        if not texts:
            raise VectorClientError("Boş metin listesi encode edilemez.")
        try:
            matrix: np.ndarray = self._model.encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return matrix.astype(self._DTYPE)
        except Exception as exc:
            raise VectorClientError(f"Batch embed işlemi başarısız: {exc}") from exc

    # ------------------------------------------------------------------
    # Similarity
    # ------------------------------------------------------------------

    def cosine_similarity(self, vec_a: np.ndarray, vec_b: np.ndarray) -> float:
        """
        Normalize edilmiş iki vektör arasındaki cosine benzerliğini döndürür.

        Normalize embeddings (normalize_embeddings=True) kullanıldığında
        cosine similarity = dot product'tır.

        Args:
            vec_a: shape=(768,) float32 vektör.
            vec_b: shape=(768,) float32 vektör.

        Returns:
            0.0–1.0 arası float (1.0 = özdeş).

        Raises:
            VectorClientError: Vektör boyutları uyuşmazsa.
        """
        if vec_a.shape != vec_b.shape:
            raise VectorClientError(
                f"Vektör boyutları uyuşmuyor: {vec_a.shape} vs {vec_b.shape}"
            )
        similarity: float = float(np.dot(vec_a, vec_b))
        # Normalize edilmiş vektörler için dot product [-1, 1] aralığındadır,
        # ancak L2-normalize sonrası pratik aralık [0, 1]'dir.
        return max(0.0, min(1.0, similarity))

    # ------------------------------------------------------------------
    # BLOB ↔ ndarray (SQLite / DB serileştirme)
    # ------------------------------------------------------------------

    def to_bytes(self, vector: np.ndarray) -> bytes:
        """
        ndarray'i SQLite'a yazılabilir ham bytes (BLOB) haline getirir.

        Args:
            vector: shape=(768,) float32 ndarray.

        Returns:
            bytes — DB'ye yazılacak BLOB.

        Raises:
            VectorClientError: Dönüşüm başarısız olursa.
        """
        try:
            return vector.astype(self._DTYPE).tobytes()
        except Exception as exc:
            raise VectorClientError(f"Vektör bytes'a dönüştürülemedi: {exc}") from exc

    def from_bytes(self, blob: bytes) -> np.ndarray:
        """
        SQLite'tan okunan ham bytes (BLOB) değerini ndarray'e geri çevirir.

        Args:
            blob: DB'den okunan BLOB değeri.

        Returns:
            shape=(768,) dtype=float32 ndarray.

        Raises:
            VectorClientError: Dönüşüm başarısız olursa veya boyut yanlışsa.
        """
        try:
            vector = np.frombuffer(blob, dtype=self._DTYPE)
        except Exception as exc:
            raise VectorClientError(f"BLOB ndarray'e dönüştürülemedi: {exc}") from exc

        if vector.shape[0] != self.VECTOR_DIM:
            raise VectorClientError(
                f"Beklenen boyut {self.VECTOR_DIM}, okunan: {vector.shape[0]}. "
                "BLOB bozuk olabilir."
            )
        return vector


vector_client = VectorClient()  # Modül yüklendiğinde tek örnek oluşturulur
