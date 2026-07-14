"""
Knowledge Graph local para O*NET y ESCO.
Carga datos desde archivos JSON/CSV procesados en data/processed.
Sirve para enriquecer Coach IA y Match Inteligente con competencias y ocupaciones.
"""
import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Any
from app.services.embeddings import get_embeddings_sync

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "processed"


class KnowledgeGraph:
    def __init__(self):
        self.onet_occupations: Dict[str, Dict] = {}
        self.onet_skills: Dict[str, List[Dict]] = {}
        self.onet_embeddings: Dict[str, List[float]] = {}
        self.onet_texts: Dict[str, str] = {}
        self.onet_related: Dict[str, List[str]] = {}

        self.esco_occupations: Dict[str, Dict] = {}
        self.esco_skills: Dict[str, List[Dict]] = {}
        self.esco_embeddings: Dict[str, List[float]] = {}
        self.esco_texts: Dict[str, str] = {}

        self.spe_embeddings: Dict[str, List[float]] = {}
        self.spe_occupations: Dict[str, str] = {}

        self._load()

    def _load(self):
        # O*NET occupations
        occ_path = DATA / "onet" / "onet_occupations.csv"
        if occ_path.exists():
            df = pd.read_csv(occ_path)
            for _, row in df.iterrows():
                self.onet_occupations[row["onet_soc_code"]] = {
                    "code": row["onet_soc_code"],
                    "title": row["title"],
                    "description": row.get("description", ""),
                    "source": "onet",
                }

        # O*NET skills
        skills_path = DATA / "onet" / "onet_occupation_skills.csv"
        if skills_path.exists():
            df = pd.read_csv(skills_path)
            for _, row in df.iterrows():
                code = row["onet_soc_code"]
                self.onet_skills.setdefault(code, []).append({
                    "element_id": row["element_id"],
                    "element_name": row["element_name"],
                    "domain": row["domain"],
                    "scale_id": row.get("scale_id"),
                    "data_value": row.get("data_value"),
                    "is_essential": bool(row.get("is_essential", False)),
                    "is_software": bool(row.get("is_software", False)),
                    "hot_technology": row.get("hot_technology"),
                    "in_demand": row.get("in_demand"),
                })

        # O*NET related occupations
        related_path = DATA / "onet" / "onet_related_occupations.csv"
        if related_path.exists():
            df = pd.read_csv(related_path)
            for _, row in df.iterrows():
                code = row["onet_soc_code"]
                rel = row["related_onet_soc_code"]
                self.onet_related.setdefault(code, []).append(rel)

        # O*NET embeddings
        emb_path = DATA / "embeddings" / "onet_occupations_embeddings.json"
        if emb_path.exists():
            with open(emb_path, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    self.onet_embeddings[item["onet_soc_code"]] = item["embedding"]
                    self.onet_texts[item["onet_soc_code"]] = item["texto"]

        # ESCO occupations
        esco_occ_path = DATA / "esco" / "esco_occupations.csv"
        if esco_occ_path.exists():
            df = pd.read_csv(esco_occ_path)
            for _, row in df.iterrows():
                self.esco_occupations[row["uri"]] = {
                    "uri": row["uri"],
                    "code": row.get("code"),
                    "title": row.get("title_es") or row["title"],
                    "title_en": row.get("title"),
                    "description": row.get("description", ""),
                    "source": "esco",
                }

        # ESCO skills
        esco_skills_path = DATA / "esco" / "esco_occupation_skills.csv"
        if esco_skills_path.exists():
            df = pd.read_csv(esco_skills_path)
            for _, row in df.iterrows():
                uri = row["esco_uri"]
                self.esco_skills.setdefault(uri, []).append({
                    "skill_uri": row["esco_skill_uri"],
                    "relation_type": row["relation_type"],
                })

        # ESCO skill definitions
        esco_skill_defs_path = DATA / "esco" / "esco_skills.csv"
        self.esco_skill_defs: Dict[str, Dict] = {}
        if esco_skill_defs_path.exists():
            df = pd.read_csv(esco_skill_defs_path)
            for _, row in df.iterrows():
                self.esco_skill_defs[row["uri"]] = {
                    "uri": row["uri"],
                    "title": row.get("title_es") or row["title"],
                    "title_en": row.get("title"),
                    "description": row.get("description", ""),
                    "skill_type": row.get("skill_type"),
                }

        # ESCO embeddings
        esco_emb_path = DATA / "embeddings" / "esco_occupations_embeddings.json"
        if esco_emb_path.exists():
            with open(esco_emb_path, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    self.esco_embeddings[item["esco_uri"]] = item["embedding"]
                    self.esco_texts[item["esco_uri"]] = item["texto"]

        # SPE embeddings
        spe_emb_path = DATA / "embeddings" / "spe_occupations_embeddings.json"
        if spe_emb_path.exists():
            with open(spe_emb_path, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    key = item.get("ocupacion") or item.get("texto")
                    self.spe_embeddings[key] = item["embedding"]
                    self.spe_occupations[key] = item.get("ocupacion", key)

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        a = np.array(a)
        b = np.array(b)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

    def _search_with_embedding(
        self,
        query_embedding: List[float],
        embeddings: Dict[str, List[float]],
        texts: Dict[str, str],
        occupations: Dict[str, Dict],
        top_k: int = 5,
    ) -> List[Dict]:
        scores = []
        for key, emb in embeddings.items():
            score = self._cosine_similarity(query_embedding, emb)
            scores.append((key, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        results = []
        for key, score in scores[:top_k]:
            occ = occupations.get(key, {})
            results.append({
                "id": key,
                "source": occ.get("source", "unknown"),
                "title": occ.get("title") or occ.get("title_es") or key,
                "description": occ.get("description", ""),
                "similarity": round(score, 4),
            })
        return results

    def search_occupations(self, query: str, top_k: int = 5) -> List[Dict]:
        """Busca ocupaciones similares en O*NET y ESCO."""
        embeddings = get_embeddings_sync([query])
        query_embedding = embeddings[0]

        onet_results = self._search_with_embedding(
            query_embedding, self.onet_embeddings, self.onet_texts, self.onet_occupations, top_k
        )
        esco_results = self._search_with_embedding(
            query_embedding, self.esco_embeddings, self.esco_texts, self.esco_occupations, top_k
        )

        # Combinar y ordenar
        combined = onet_results + esco_results
        combined.sort(key=lambda x: x["similarity"], reverse=True)
        return combined[:top_k]

    def get_skills(self, occupation_id: str, source: str = "auto", top_n: int = 10) -> List[Dict]:
        """Devuelve las principales skills de una ocupación."""
        if source == "auto":
            if occupation_id in self.onet_occupations:
                source = "onet"
            elif occupation_id in self.esco_occupations:
                source = "esco"
            else:
                return []

        if source == "onet":
            skills = self.onet_skills.get(occupation_id, [])
            # Priorizar esenciales y software hot/in-demand
            def _safe_value(s, key):
                v = s.get(key)
                if v is None:
                    return 0.0
                try:
                    v = float(v)
                    if not np.isfinite(v):
                        return 0.0
                    return v
                except (ValueError, TypeError):
                    return 0.0

            skills = sorted(
                skills,
                key=lambda s: (
                    s.get("is_essential", False),
                    s.get("hot_technology") == "Y",
                    s.get("in_demand") == "Y",
                    _safe_value(s, "data_value"),
                ),
                reverse=True,
            )
            return [
                {
                    "name": s["element_name"],
                    "domain": s["domain"],
                    "is_essential": s["is_essential"],
                    "is_software": s["is_software"],
                    "level": _safe_value(s, "data_value") or None,
                    "hot_technology": s.get("hot_technology"),
                    "in_demand": s.get("in_demand"),
                }
                for s in skills[:top_n]
            ]
        else:
            relations = self.esco_skills.get(occupation_id, [])
            # Priorizar esenciales
            relations = sorted(relations, key=lambda r: r["relation_type"] == "essential", reverse=True)
            results = []
            for rel in relations[:top_n]:
                skill_def = self.esco_skill_defs.get(rel["skill_uri"], {})
                results.append({
                    "name": skill_def.get("title") or rel["skill_uri"],
                    "domain": skill_def.get("skill_type", "skill"),
                    "is_essential": rel["relation_type"] == "essential",
                    "is_software": False,
                    "description": skill_def.get("description", ""),
                })
            return results

    def skill_gap(
        self,
        user_skills: List[str],
        occupation_id: str,
        source: str = "auto",
    ) -> Dict[str, Any]:
        """Compara skills del usuario con los requeridos por una ocupación."""
        required = self.get_skills(occupation_id, source, top_n=50)
        user_lower = [s.lower().strip() for s in user_skills]

        has = []
        missing = []
        for req in required:
            req_name = req["name"].lower().strip()
            # Coincidencia exacta o subcadena
            match = any(req_name in us or us in req_name for us in user_lower)
            if match:
                has.append(req)
            else:
                missing.append(req)

        return {
            "occupation_id": occupation_id,
            "occupation_title": (
                self.onet_occupations.get(occupation_id, {}).get("title")
                or self.esco_occupations.get(occupation_id, {}).get("title")
                or occupation_id
            ),
            "total_required": len(required),
            "matched": has,
            "missing": missing,
            "match_percentage": round(len(has) / len(required) * 100, 1) if required else 0,
        }

    def suggest_occupations_from_skills(self, user_skills: List[str], top_k: int = 5) -> List[Dict]:
        """Sugiere ocupaciones basadas en un conjunto de habilidades del usuario."""
        query = ", ".join(user_skills)
        return self.search_occupations(query, top_k)

    def get_related_occupations(self, onet_soc_code: str, top_k: int = 5) -> List[Dict]:
        """Devuelve ocupaciones relacionadas según O*NET."""
        related_codes = self.onet_related.get(onet_soc_code, [])[:top_k]
        results = []
        for code in related_codes:
            occ = self.onet_occupations.get(code, {})
            if occ:
                results.append({
                    "id": code,
                    "source": "onet",
                    "title": occ["title"],
                    "description": occ.get("description", ""),
                })
        return results


# Singleton
_kg: Optional[KnowledgeGraph] = None


def get_knowledge_graph() -> KnowledgeGraph:
    global _kg
    if _kg is None:
        _kg = KnowledgeGraph()
    return _kg
