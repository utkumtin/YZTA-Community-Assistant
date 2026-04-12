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
• pgvector Vector(768) kolonu ile doğrudan uyumludur.

KULLANIM
--------
    from packages.vector import VectorClient

    vc  = VectorClient()                           # Singleton; model tek kez yüklenir
    vec = vc.embed("Yeni bir özellik istiyorum")   # ndarray shape=(768,)
    sim = vc.cosine_similarity(vec, vec2)          # float [0.0, 1.0]

    # DB'ye yazma (SQLAlchemy + pgvector):
    feature_request.request_embedded = vec.tolist()   # veya doğrudan ndarray

HATA YÖNETİMİ
--------------
• Model yüklenemezse VectorClientError fırlatır.
• Encode işlemi başarısız olursa VectorClientError fırlatır.

MODEL
-----
  paraphrase-multilingual-mpnet-base-v2
    - 768 boyutlu dense vektör çıktısı
    - 50+ dil desteği (Türkçe dahil)
    - ~420 MB (ilk çalıştırmada HuggingFace'den indirilir, sonrası cache)
"""

import numpy as np
from sentence_transformers import SentenceTransformer

class VectorClientError(Exception):
    """Vector client operations için temel hata sınıfı."""
    pass

class SingletonMeta(type):
    """Sınıfın sadece tek bir örneğinin (singleton) olmasını sağlayan metaclass."""
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

from packages.logger.manager import get_logger
logger = get_logger("vector_client")


class VectorClient(metaclass=SingletonMeta):
    """
    sentence-transformers tabanlı Singleton embedding istemcisi.

    İlk örneklendiğinde modeli yükler (~420 MB, bir kez). Sonraki
    çağrılar aynı yüklü modeli kullanır.

    pgvector entegrasyonu: embed() ve embed_batch() çıktısı olduğu gibi
    SQLAlchemy Vector(768) kolonuna atanabilir; ayrıca serileştirme gerekmez.
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

    # Encode

    def embed(self, text: str) -> np.ndarray:
        """
        Tek bir metni 768 boyutlu float32 vektöre dönüştürür.

        Dönen ndarray doğrudan pgvector Vector(768) kolonuna atanabilir;
        SQLAlchemy dönüşümü otomatik yapar.

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

    # Similarity

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
