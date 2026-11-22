"""Pangkalan Data Undang-Undang Tepat (Strict Statutory RAG).

Mengindeks teks verbatim akta dalam `data/akta/` (Akta 852, Akta Makanan 1983,
Akta 154, Akta 342, Kanun Tatacara Jenayah [Akta 593], dan Akta Keterangan 1950)
menggunakan gabungan ChromaDB + Okapi BM25 dengan Stemmer Bahasa Melayu Undang-Undang.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pymupdf as fitz

from backend.core.config import settings

try:
    import chromadb
    from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

    CHROMADB_AVAILABLE = True
except Exception:
    chromadb = None  # type: ignore
    Documents = Any  # type: ignore
    EmbeddingFunction = object  # type: ignore
    Embeddings = Any  # type: ignore
    CHROMADB_AVAILABLE = False


TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")

# Pemetaan kata akar undang-undang Bahasa Melayu (untuk padanan tepat BM25)
MALAY_LEGAL_ROOTS = {
    "mempamerkan": "pamer",
    "pameran": "pamer",
    "dipamerkan": "pamer",
    "mengiklankan": "iklan",
    "pengiklanan": "iklan",
    "iklan": "iklan",
    "menyita": "sita",
    "penyitaan": "sita",
    "disita": "sita",
    "sitaan": "sita",
    "membiak": "biak",
    "membiakkan": "biak",
    "pembiakan": "biak",
    "mengkompaun": "kompaun",
    "pengkompaunan": "kompaun",
    "dikompaun": "kompaun",
    "menjual": "jual",
    "penjualan": "jual",
    "dijual": "jual",
    "merokok": "rokok",
    "perokok": "rokok",
    "pendakwaan": "dakwa",
    "mendakwa": "dakwa",
    "pertuduhan": "tuduh",
    "dipertuduh": "tuduh",
    "tertubuh": "tubuh",
    "penutupan": "tutup",
    "ditutup": "tutup",
    "kebersihan": "bersih",
    "membersihkan": "bersih",
    "pembersihan": "bersih",
    "vaksinasi": "tifoid",
    "suntikan": "tifoid",
    "pengendali": "kendali",
    "mengendalikan": "kendali",
    "perakuan": "aku",
    "memperakukan": "aku",
    "computer": "komputer",
    "computers": "komputer",
    "komputer": "komputer",
    "publication": "penerbitan",
    "penerbitan": "penerbitan",
}

MALAY_STOPWORDS = {
    "yang", "dan", "atau", "di", "ke", "dari", "daripada", "pada", "dalam",
    "untuk", "dengan", "oleh", "adalah", "ialah", "apa", "mana", "mana-mana",
    "suatu", "jika", "tidak", "tiada", "boleh", "hendaklah", "telah", "ini", "itu",
    "kepada", "ada", "akan", "sudah", "sedang", "masih", "sahaja", "saja", "kah",
    "lah", "pun", "nak", "bolehkah", "adakah", "apakah", "bagaimana", "kenapa",
    "kalau", "bila", "apabila", "tersebut", "secara", "terhadap", "mengenai",
    "tentang", "juga", "lagi", "hanya", "belum", "pernah", "kerana", "sebab",
    "tetapi", "tapi", "namun", "supaya", "agar",
}

MALAY_QUERY_NORMALIZATIONS = {
    "datng": "datang",
    "taknak": "enggan",
    "xnak": "enggan",
    "xde": "tiada",
    "yg": "yang",
    "dgn": "dengan",
    "utk": "untuk",
    "org": "orang",
    "bdk": "budak",
    "sbb": "sebab",
    "covid19": "covid",
    "covid-19": "covid",
}

STEM_PROTECTED = {"majikan", "makan", "bukan", "ikan", "rakan", "pekerja", "saringan"}


def _normalize_query_text(text: str) -> str:
    norm = (text or "").lower()
    for src, dst in MALAY_QUERY_NORMALIZATIONS.items():
        norm = re.sub(rf"(?<!\w){re.escape(src)}(?!\w)", dst, norm)
    return norm


def _stem_malay_legal(word: str) -> str:
    low = word.lower()
    if low in MALAY_LEGAL_ROOTS:
        return MALAY_LEGAL_ROOTS[low]
    if low in STEM_PROTECTED:
        return low
    # Potong imbuhan akhiran biasa
    for suf in ("kan", "an", "nya", "i"):
        if len(low) > 6 and low.endswith(suf):
            low = low[: -len(suf)]
            break
    # Potong imbuhan awalan biasa
    for pref in ("peng", "peny", "pem", "pen", "meng", "meny", "mem", "men", "per", "ber", "ter", "di", "me"):
        if len(low) > 6 and low.startswith(pref):
            low = low[len(pref) :]
            break
    return MALAY_LEGAL_ROOTS.get(low, low)


def _tokenize(text: str) -> List[str]:
    norm_text = _normalize_query_text(text)
    raw_tokens = [t.lower() for t in TOKEN_RE.findall(norm_text)]
    tokens: List[str] = []
    for t in raw_tokens:
        if t in MALAY_STOPWORDS:
            continue
        tokens.append(t)
        stemmed = _stem_malay_legal(t)
        if stemmed != t and len(stemmed) >= 3:
            tokens.append(stemmed)
    return tokens


class _DeterministicHashEmbedding(EmbeddingFunction):  # type: ignore[misc]
    """Penjana vektor hash deterministik luar talian dengan sokongan kata akar Melayu."""

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim

    @staticmethod
    def name() -> str:
        return "uip_malay_legal_hash"

    def get_config(self) -> Dict[str, Any]:
        return {"dim": self.dim}

    def __call__(self, input: Documents) -> Embeddings:  # noqa: A002
        vectors: List[List[float]] = []
        for doc in input:
            vec = [0.0] * self.dim
            tokens = _tokenize(doc)
            terms = tokens + [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]
            for term in terms:
                digest = hashlib.sha256(term.encode("utf-8")).digest()
                idx = int.from_bytes(digest[:4], "little") % self.dim
                sign = 1.0 if (digest[4] & 1) == 0 else -1.0
                vec[idx] += sign
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vectors.append([v / norm for v in vec])
        return vectors


@dataclass
class StatuteChunk:
    chunk_id: str
    akta_code: str
    akta_title: str
    section: str
    text: str
    source_file: str
    score: float = 0.0
    max_fine_hint: str = ""
    is_compoundable_hint: str = ""


def _infer_akta_metadata(filename: str, content: str) -> tuple[str, str]:
    stem = Path(filename).stem.lower()
    low = (stem + " " + content[:600]).lower()
    if "akta_342" in stem or "akta 342" in low or "342" in stem or "penyakit berjangkit" in low or "apppb" in low:
        return "Akta 342", "Akta Pencegahan dan Pengawalan Penyakit Berjangkit 1988 [Akta 342]"
    if "akta_154" in stem or "akta 154" in low or "154" in stem or "serangga pembawa penyakit" in low or "aedes" in low:
        return "Akta 154", "Akta Pemusnahan Serangga Pembawa Penyakit 1975 [Akta 154]"
    if "akta_852" in stem or "akta 852" in low or "852" in stem or "produk merokok" in low:
        return "Akta 852", "Akta Kawalan Produk Merokok Demi Kesihatan Awam 2024 [Akta 852]"
    if "akta_611" in stem or "akta 611" in low or "611" in stem or "kanak-kanak 2001" in low:
        return "Akta 611", "Akta Kanak-Kanak 2001 [Akta 611]"
    if "akta 171" in low or "171" in stem or "kerajaan tempatan" in low:
        return "Akta 171", "Akta Kerajaan Tempatan 1976 [Akta 171]"
    if "akta 366" in low or "366" in stem or "racun" in low or "akta 368" in low:
        return "Akta 366", "Akta Racun 1952 [Akta 366] & Akta Jualan Dadah 1952"
    if "akta 586" in low or "586" in stem or "jagaan kesihatan swasta" in low:
        return "Akta 586", "Akta Kemudahan dan Perkhidmatan Jagaan Kesihatan Swasta 1998 [Akta 586]"
    if "akta 260" in low or "260" in stem or "hidrogen sianida" in low:
        return "Akta 260", "Akta Hidrogen Sianida (Pengasapan) 1953 [Akta 260]"
    if "akta 127" in low or "127" in stem or "kualiti alam sekeliling" in low:
        return "Akta 127", "Akta Kualiti Alam Sekeliling 1974 [Akta 127] & Akta 655"
    if (
        "akta_281" in stem
        or "ppkm" in stem
        or "ppm_" in stem
        or "akta 281" in low
        or "akta makanan" in low
        or "kebersihan makanan" in low
        or "peraturan-peraturan makanan 1985" in low
    ):
        return "Akta 281", "Akta Makanan 1983 [Akta 281] & Peraturan Kebersihan Makanan 2009"
    if "akta_593" in stem or "593" in stem or "tatacara jenayah" in low or "criminal procedure code" in low or "ktj" in low:
        return "Akta 593", "Kanun Tatacara Jenayah [Akta 593]"
    if "akta_56" in stem or "56" == stem or "90a" in low or "keterangan 1950" in low or "akta 56" in low or "evidence act 1950" in low:
        return "Akta 56", "Akta Keterangan 1950 [Akta 56]"
    return Path(filename).stem, Path(filename).stem.replace("_", " ").title()


def _extract_legal_hints(block: str) -> tuple[str, str]:
    fine_m = re.search(r"(?:didenda|denda|fine)[^.\n;]*(RM\s?[\d,]+|ringgit)", block, flags=re.I)
    fine_hint = fine_m.group(0).strip()[:90] if fine_m else ""
    comp_hint = "Boleh kompaun" if ("kompaun" in block.lower() or "compound" in block.lower()) else ""
    return fine_hint, comp_hint


def _split_into_section_chunks(
    text: str, filename: str, akta_code: str, akta_title: str
) -> List[StatuteChunk]:
    if filename.lower().endswith(".pdf"):
        from backend.rag.legal_engine import (
            infer_statute_id_from_filename_or_text,
            parse_statute_verbatim_sections,
        )

        sid = infer_statute_id_from_filename_or_text(filename, text)
        parsed_secs, _ = parse_statute_verbatim_sections(
            raw_text=text,
            default_statute_id=sid,
            source_filename=filename,
        )
        chunks: List[StatuteChunk] = []
        for idx, sec in enumerate(parsed_secs):
            sec_code = str(sec.get("section_code") or "").strip()
            sec_heading = str(sec.get("section_heading") or "").strip()
            verbatim = str(sec.get("verbatim_text_bm") or "").strip()
            if len(verbatim) < 25:
                continue
            if sec_code.lower().startswith(("seksyen", "peraturan", "jadual", "first", "second", "third")):
                sec_lbl = sec_code
            else:
                sec_lbl = f"Seksyen {sec_code}"
            if sec_heading and sec_heading.lower() not in sec_lbl.lower():
                sec_lbl = f"{sec_lbl} — {sec_heading[:70]}"
            fine_hint, comp_hint = _extract_legal_hints(verbatim)
            chunks.append(
                StatuteChunk(
                    chunk_id=str(sec.get("doc_id") or f"{Path(filename).stem}__chunk_{idx:03d}"),
                    akta_code=akta_code,
                    akta_title=akta_title,
                    section=sec_lbl[:110],
                    text=verbatim,
                    source_file=filename,
                    max_fine_hint=fine_hint,
                    is_compoundable_hint=comp_hint,
                )
            )
        return chunks

    blocks = re.split(
        r"\n(?=(?:Seksyen|Peraturan|-\s*Seksyen|-\s*Peraturan|Keperluan|Akta)\s+)",
        text.strip(),
    )
    chunks = []
    is_multi_act_file = "lain_rujukan" in filename.lower()
    for idx, block in enumerate(blocks):
        clean_block = block.strip()
        if len(clean_block) < 40:
            continue
        first_line = clean_block.splitlines()[0].lstrip("- ").strip()
        sec_match = re.match(
            r"^((?:Seksyen|Peraturan|Akta)\s+[0-9A-Za-z\(\),&\s]+?)(?:\s*(?:[-–—:]|\[)|$)",
            first_line,
            flags=re.I,
        )
        section_label = sec_match.group(1).strip() if sec_match else first_line[:70]
        chunk_akta_code, chunk_akta_title = (
            _infer_akta_metadata(filename, clean_block)
            if is_multi_act_file
            else (akta_code, akta_title)
        )
        fine_hint, comp_hint = _extract_legal_hints(clean_block)
        chunk_id = f"{Path(filename).stem}__chunk_{idx:03d}"
        chunks.append(
            StatuteChunk(
                chunk_id=chunk_id,
                akta_code=chunk_akta_code,
                akta_title=chunk_akta_title,
                section=section_label,
                text=clean_block,
                source_file=filename,
                max_fine_hint=fine_hint,
                is_compoundable_hint=comp_hint,
            )
        )
    return chunks


class StatutoryRAGStore:
    """Stor RAG Statutori menggunakan ChromaDB + Okapi BM25 Melayu."""

    COLLECTION_NAME = "uip_statutory_acts"
    CACHE_SCHEMA_VERSION = "3.1-agc-pdf"

    def __init__(
        self,
        akta_dir: Optional[Path] = None,
        persist_dir: Optional[Path] = None,
    ) -> None:
        self.akta_dir = Path(akta_dir or settings.akta_dir)
        self.persist_dir = Path(persist_dir or settings.chroma_persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.akta_dir.mkdir(parents=True, exist_ok=True)

        self._chunks: List[StatuteChunk] = []
        self._doc_freqs: Counter[str] = Counter()
        self._chunk_counters: Dict[str, Counter[str]] = {}
        self._chunk_lengths: Dict[str, int] = {}
        self._avg_doc_len: float = 1.0
        self._engine: str = "uninitialized"
        self._chroma_client = None
        self._collection = None

        self._init_store()
        self.ingest_directory()

    @property
    def engine_name(self) -> str:
        return self._engine

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    def _init_store(self) -> None:
        if CHROMADB_AVAILABLE:
            try:
                self._chroma_client = chromadb.PersistentClient(path=str(self.persist_dir))
                self._collection = self._chroma_client.get_or_create_collection(
                    name=self.COLLECTION_NAME,
                    embedding_function=_DeterministicHashEmbedding(),
                    metadata={"hnsw:space": "cosine"},
                )
                self._engine = "chromadb-persistent"
                return
            except Exception:
                self._chroma_client = None
                self._collection = None
        self._engine = "okapi-bm25-tempatan"

    @staticmethod
    def extract_text_from_file(file_path: Path) -> str:
        if file_path.suffix.lower() == ".pdf":
            pages: List[str] = []
            with fitz.open(file_path) as doc:
                for page in doc:
                    pages.append(page.get_text("text"))
            return "\n".join(pages)
        return file_path.read_text(encoding="utf-8", errors="ignore")

    def _compute_dir_fingerprint(self) -> str:
        from backend.rag.legal_engine import PARSER_VERSION

        parts: List[str] = [self.CACHE_SCHEMA_VERSION, PARSER_VERSION]
        for path in sorted(self.akta_dir.glob("*")):
            if path.suffix.lower() not in (".txt", ".pdf"):
                continue
            if path.name.upper().startswith("PANDUAN_"):
                continue
            st = path.stat()
            parts.append(f"{path.name}:{st.st_size}:{hashlib.sha256(path.read_bytes()).hexdigest()[:16]}")
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()

    def ingest_directory(self) -> int:
        dir_fp = self._compute_dir_fingerprint()
        cache_path = self.persist_dir / "statutory_chunks_cache.json"
        if cache_path.exists():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                if cached.get("fingerprint") == dir_fp and isinstance(cached.get("chunks"), list) and cached["chunks"]:
                    self._chunks = [StatuteChunk(**item) for item in cached["chunks"]]
                    self._build_bm25_index()
                    return len(self._chunks)
            except Exception:
                pass

        all_paths = [
            p
            for p in sorted(self.akta_dir.glob("*"))
            if p.suffix.lower() in (".pdf", ".txt") and not p.name.upper().startswith("PANDUAN_")
        ]
        ordered_paths = [p for p in all_paths if p.suffix.lower() == ".pdf"] + [
            p for p in all_paths if p.suffix.lower() == ".txt"
        ]

        all_chunks: List[StatuteChunk] = []
        pdf_covered_acts: set[str] = set()
        seen_chunk_ids: set[str] = set()

        for path in ordered_paths:
            is_pdf = path.suffix.lower() == ".pdf"
            content = self.extract_text_from_file(path)
            if not content.strip():
                continue
            akta_code, akta_title = _infer_akta_metadata(path.name, content)
            file_chunks = _split_into_section_chunks(content, path.name, akta_code, akta_title)
            for c in file_chunks:
                if not is_pdf and c.akta_code in pdf_covered_acts:
                    continue
                if c.chunk_id in seen_chunk_ids:
                    c.chunk_id = f"{c.chunk_id}_{len(seen_chunk_ids)}"
                seen_chunk_ids.add(c.chunk_id)
                all_chunks.append(c)
                if is_pdf:
                    pdf_covered_acts.add(c.akta_code)

        self._chunks = all_chunks
        self._build_bm25_index()

        # Simpan cache cakera untuk startup pantas (<0.1s)
        try:
            cache_path.write_text(
                json.dumps(
                    {
                        "fingerprint": dir_fp,
                        "chunks": [
                            {
                                "chunk_id": c.chunk_id,
                                "akta_code": c.akta_code,
                                "akta_title": c.akta_title,
                                "section": c.section,
                                "text": c.text,
                                "source_file": c.source_file,
                                "max_fine_hint": c.max_fine_hint,
                                "is_compoundable_hint": c.is_compoundable_hint,
                            }
                            for c in all_chunks
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass

        if self._collection is not None and all_chunks:
            if self._chroma_client is not None:
                try:
                    self._chroma_client.delete_collection(name=self.COLLECTION_NAME)
                    self._collection = self._chroma_client.get_or_create_collection(
                        name=self.COLLECTION_NAME,
                        embedding_function=_DeterministicHashEmbedding(),
                        metadata={"hnsw:space": "cosine"},
                    )
                except Exception:
                    pass
            batch_size = 200
            for start in range(0, len(all_chunks), batch_size):
                batch = all_chunks[start : start + batch_size]
                self._collection.upsert(
                    ids=[c.chunk_id for c in batch],
                    documents=[c.text[:4000] for c in batch],
                    metadatas=[
                        {
                            "akta_code": c.akta_code,
                            "akta_title": c.akta_title,
                            "section": c.section,
                            "source_file": c.source_file,
                        }
                        for c in batch
                    ],
                )
        else:
            fallback_path = self.persist_dir / "statutory_fallback_index.json"
            fallback_path.write_text(
                json.dumps(
                    [
                        {
                            "chunk_id": c.chunk_id,
                            "akta_code": c.akta_code,
                            "akta_title": c.akta_title,
                            "section": c.section,
                            "text": c.text,
                            "source_file": c.source_file,
                        }
                        for c in all_chunks
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

        return len(all_chunks)

    def _build_bm25_index(self) -> None:
        self._doc_freqs.clear()
        self._chunk_counters.clear()
        self._chunk_lengths.clear()

        total_len = 0
        for c in self._chunks:
            toks = _tokenize(f"{c.akta_code} {c.section} {c.text[:3000]}")
            cnt = Counter(toks)
            self._chunk_counters[c.chunk_id] = cnt
            self._chunk_lengths[c.chunk_id] = len(toks)
            total_len += len(toks)
            for term in cnt.keys():
                self._doc_freqs[term] += 1

        self._avg_doc_len = (total_len / len(self._chunks)) if self._chunks else 1.0

    def ingest_uploaded_file(self, filename: str, raw_bytes: bytes) -> int:
        safe_name = Path(filename).name
        target_path = self.akta_dir / safe_name
        target_path.write_bytes(raw_bytes)
        return self.ingest_directory()

    def list_available_acts(self) -> List[Dict[str, str]]:
        seen: Dict[str, Dict[str, str]] = {}
        for chunk in self._chunks:
            if chunk.akta_code not in seen:
                seen[chunk.akta_code] = {
                    "akta_code": chunk.akta_code,
                    "akta_title": chunk.akta_title,
                    "source_file": chunk.source_file,
                }
        return list(seen.values())

    @staticmethod
    def _infer_domain_signals(query: str) -> tuple[Optional[str], List[str]]:
        """Mengenal pasti isyarat domain kuat & istilah perluasan ringan apabila penapis='Semua'."""
        q_norm = _normalize_query_text(query)
        domain_rules: Dict[str, tuple[tuple[str, ...], List[str]]] = {
            "Akta 342": (
                (
                    "covid", "koronavirus", "cdc", "hso", "kuarantin", "pengasingan", "isolasi",
                    "wabak", "berjangkit", "tibi", "ptb", "afb", "tbis", "hfmd", "leptospirosis",
                    "measles", "campak", "kolera", "difteria", "influenza", "mpox", "rabies",
                    "kontak rapat", "e-notifikasi", "enotifikasi", "apppb", "a1742",
                ),
                ["penyakit", "berjangkit", "342", "pengawasan", "perintah"],
            ),
            "Akta 852": (
                ("rokok", "vape", "pod", "shisha", "obd", "ashtray", "merokok", "257", "259", "260"),
                ["merokok", "852"],
            ),
            "Akta 281": (
                ("makanan", "restoran", "dapur", "tifoid", "lpm", "slpm", "fosim", "keracunan", "najis tikus", "lipas", "luput", "mja", "ppkm", "ppm"),
                ["makanan", "281"],
            ),
            "Akta 154": (
                ("aedes", "denggi", "jentik", "larva", "nyamuk", "fogging", "entomologi", "tapak bina"),
                ["aedes", "154"],
            ),
        }
        scores: Dict[str, int] = {}
        expansions: Dict[str, List[str]] = {}
        for act, (terms, exp) in domain_rules.items():
            hits = sum(1 for term in terms if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", q_norm))
            if hits > 0:
                scores[act] = hits
                expansions[act] = exp
        if not scores:
            return None, []
        top_act = max(scores, key=lambda k: scores[k])
        return top_act, expansions[top_act]

    def search_statutes(
        self,
        query: str,
        akta_filter: Optional[str] = None,
        top_k: int = 4,
    ) -> List[StatuteChunk]:
        if not self._chunks:
            return []

        norm_filter = (akta_filter or "").strip().lower()
        if norm_filter in ("", "semua", "all"):
            norm_filter = ""

        domain_act, domain_expansions = (None, []) if norm_filter else self._infer_domain_signals(query)

        chroma_scores: Dict[str, float] = {}
        if self._collection is not None:
            try:
                where_clause = None
                if norm_filter:
                    matched_codes = {
                        c.akta_code
                        for c in self._chunks
                        if norm_filter in c.akta_code.lower() or norm_filter in c.akta_title.lower()
                    }
                    if len(matched_codes) == 1:
                        where_clause = {"akta_code": next(iter(matched_codes))}
                res = self._collection.query(
                    query_texts=[_normalize_query_text(query)],
                    n_results=min(max(top_k * 3, 8), len(self._chunks)),
                    where=where_clause,
                )
                ids = res.get("ids", [[]])[0]
                distances = res.get("distances", [[]])[0]
                for cid, dist in zip(ids, distances):
                    chroma_scores[cid] = max(0.0, 1.0 - float(dist))
            except Exception:
                chroma_scores = {}

        query_tokens = _tokenize(query)
        unique_q_tokens = set(query_tokens)
        expansion_tokens = set(domain_expansions) - unique_q_tokens
        n_docs = len(self._chunks)
        k1 = 1.5
        b = 0.75

        raw_bm25: Dict[str, float] = {}
        for chunk in self._chunks:
            if norm_filter:
                haystack_meta = f"{chunk.akta_code} {chunk.akta_title} {chunk.source_file}".lower()
                if norm_filter not in haystack_meta:
                    continue

            c_cnt = self._chunk_counters.get(chunk.chunk_id, Counter())
            doc_len = self._chunk_lengths.get(chunk.chunk_id, 1)
            bm25 = 0.0
            for qt in unique_q_tokens:
                tf = c_cnt.get(qt, 0)
                if tf == 0:
                    continue
                df = self._doc_freqs.get(qt, 0)
                idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
                denom = tf + k1 * (1.0 - b + b * (doc_len / max(1.0, self._avg_doc_len)))
                bm25 += idf * ((tf * (k1 + 1.0)) / denom)

            for eq in expansion_tokens:
                tf = c_cnt.get(eq, 0)
                if tf == 0:
                    continue
                df = self._doc_freqs.get(eq, 0)
                idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
                denom = tf + k1 * (1.0 - b + b * (doc_len / max(1.0, self._avg_doc_len)))
                bm25 += 0.45 * idf * ((tf * (k1 + 1.0)) / denom)

            # Bonus padanan nombor seksyen atau Peraturan tepat
            sec_low = chunk.section.lower()
            for qt in unique_q_tokens:
                if qt in sec_low and (qt.isdigit() or "90a" in qt or "32b" in qt or "112" in qt):
                    bm25 += 3.0
            raw_bm25[chunk.chunk_id] = bm25

        max_bm25 = max(raw_bm25.values()) if raw_bm25 else 0.0
        bm25_denom = max(max_bm25, 4.5)

        scored: List[StatuteChunk] = []
        for chunk in self._chunks:
            if chunk.chunk_id not in raw_bm25:
                continue
            chunk_bm25 = raw_bm25[chunk.chunk_id]
            bm25_norm = chunk_bm25 / bm25_denom
            vec_score = chroma_scores.get(chunk.chunk_id, 0.0) if (chunk_bm25 > 0 or max_bm25 == 0) else 0.0
            act_boost = 0.20 if (domain_act and chunk.akta_code == domain_act) else 0.0
            combined = (0.88 * bm25_norm) + (0.12 * vec_score) + act_boost
            normalized_score = round(min(0.99, max(0.01, combined)), 4)

            scored.append(
                StatuteChunk(
                    chunk_id=chunk.chunk_id,
                    akta_code=chunk.akta_code,
                    akta_title=chunk.akta_title,
                    section=chunk.section,
                    text=chunk.text,
                    source_file=chunk.source_file,
                    score=normalized_score,
                    max_fine_hint=chunk.max_fine_hint,
                    is_compoundable_hint=chunk.is_compoundable_hint,
                )
            )

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]


_store_instance: Optional[StatutoryRAGStore] = None


def get_statutory_store() -> StatutoryRAGStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = StatutoryRAGStore()
    return _store_instance
