#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate deterministic demo candidates and analysis for sci-literature-news."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"

PROFILE = {
    "profile": {
        "name": "Анна Иванова",
        "affiliation": "Лаборатория анализа данных, пример",
        "orcid": "0000-0002-0000-0001",
        "google_scholar": "https://scholar.google.com/citations?user=example",
        "scopus": "00000000000",
        "researchgate": "—",
        "personal_site": "https://example.org/anna",
        "profile_source": "example",
        "profile_fetched_at": "2026-11-02",
    },
    "directions": [
        {"id": "D1", "direction": "Графовые нейронные сети", "query": "graph neural networks", "notes": "архитектуры, обучение, приложения"},
        {"id": "D2", "direction": "Сегментация медицинских изображений", "query": "medical image segmentation", "notes": "КТ, МРТ, микроскопия"},
        {"id": "D3", "direction": "Scientific machine learning", "query": "scientific machine learning", "notes": "нейрооператоры и физически-информированные модели"},
    ],
    "preferences": {
        "period_months": 6,
        "from": "2026-05-02",
        "to": "2026-11-02",
        "categories": ["Q1 journals", "A* conferences", "Q2 journals"],
        "languages": ["en"],
        "include_preprints": False,
        "max_results_per_direction": 100,
        "ranking_source": "SJR 2025; ICORE2026",
        "report_language": "ru",
        "last_confirmed": "2026-11-02",
    },
}


def paper(doi, title, venue, date, authors, citations, category, directions, abstract, ranking, venue_type):
    return {
        "id": doi.replace("/", "-").replace(".", "-"),
        "doi": doi,
        "title": title,
        "abstract": abstract,
        "date": date,
        "year": int(date[:4]),
        "type": "article",
        "venue": venue,
        "venue_type": venue_type,
        "issn": [],
        "authors": authors,
        "citations": citations,
        "oa_url": "",
        "url": f"https://doi.org/{doi}",
        "field": "Computer Science",
        "subfield": "Artificial Intelligence",
        "direction_ids": directions,
        "category": category,
        "ranking_evidence": [ranking],
        "sjr": {"quartile": "Q1" if category == "q1" else "Q2", "source": "SCImago SJR 2025", "year": "2025", "field": "Computer Science", "match": "field"} if category in ("q1", "q2") else None,
        "core": {"rank": "A*", "source": "ICORE2026", "match": "acronym"} if category == "a_star" else None,
        "quality": "measured",
    }


PAPERS = [
    paper(
        "10.1016/j.media.2026.103001",
        "Foundation models for medical image segmentation: a multi-centre evaluation",
        "Medical Image Analysis",
        "2026-09-12",
        ["A. Petrova", "M. Chen", "R. Singh"],
        84,
        "q1",
        ["D2"],
        "We evaluate a family of foundation models for CT and MRI segmentation across six hospitals. The best model improves the Dice score by 4.8 points on external data, but calibration remains sensitive to scanner shift.",
        "SCImago SJR 2025 · Q1 · Computer Science",
        "journal",
    ),
    paper(
        "10.1038/s42256-026-01001-1",
        "Self-supervised microscopy representation learning with limited labels",
        "Nature Machine Intelligence",
        "2026-07-03",
        ["L. Moroz", "K. Sato", "D. Williams"],
        61,
        "q1",
        ["D2"],
        "A masked-image objective learns transferable representations from unlabelled microscopy volumes. Fine-tuning with 5% of labels matches a fully supervised baseline on two external datasets.",
        "SCImago SJR 2025 · Q1 · Computer Science",
        "journal",
    ),
    paper(
        "10.1109/TPAMI.2026.1001",
        "Uncertainty-aware segmentation under distribution shift",
        "IEEE Transactions on Pattern Analysis and Machine Intelligence",
        "2026-10-01",
        ["V. Orlova", "T. Nguyen"],
        37,
        "q1",
        ["D2", "D3"],
        "The paper introduces a conformal prediction layer for segmentation masks. It provides pixel-level coverage guarantees and improves failure detection under domain shift.",
        "SCImago SJR 2025 · Q1 · Computer Science",
        "journal",
    ),
    paper(
        "10.5555/neurips.2026.001",
        "Scaling graph transformers with adaptive sparsity",
        "NeurIPS 2026",
        "2026-09-25",
        ["I. Smirnov", "H. Lee", "P. Garcia"],
        29,
        "a_star",
        ["D1"],
        "We combine graph transformers with learned sparse attention and show that the resulting model scales to million-node graphs without losing long-range dependencies. Code and configs are released.",
        "ICORE2026 · A* · NeurIPS",
        "conference",
    ),
    paper(
        "10.5555/cvpr.2026.014",
        "Test-time adaptation for medical image segmentation",
        "CVPR 2026",
        "2026-06-18",
        ["N. Ivanov", "S. Kim"],
        45,
        "a_star",
        ["D2"],
        "A lightweight test-time adaptation procedure updates normalization statistics and a small adapter at inference. It recovers 70% of the drop caused by a new scanner.",
        "ICORE2026 · A* · CVPR",
        "conference",
    ),
    paper(
        "10.5555/icml.2026.088",
        "Neural operators with physics-aware latent dynamics",
        "ICML 2026",
        "2026-07-22",
        ["E. Volkova", "J. Brown", "A. Kumar"],
        33,
        "a_star",
        ["D3"],
        "We learn a latent dynamical system constrained by conservation laws and use it as a neural operator for parametric PDEs. The model generalizes to unseen boundary conditions with a 3x data reduction.",
        "ICORE2026 · A* · ICML",
        "conference",
    ),
    paper(
        "10.1016/j.cmpb.2026.108001",
        "Lightweight segmentation for point-of-care ultrasound",
        "Computer Methods and Programs in Biomedicine",
        "2026-08-14",
        ["O. Sokolova", "R. Mehta"],
        18,
        "q2",
        ["D2"],
        "A compact U-Net variant runs on a mobile GPU while preserving 96% of the baseline Dice score. The authors release an annotated point-of-care ultrasound subset.",
        "SCImago SJR 2025 · Q2 · Medicine",
        "journal",
    ),
    paper(
        "10.1016/j.jbi.2026.104501",
        "Benchmarking graph learning for clinical prediction",
        "Journal of Biomedical Informatics",
        "2026-06-30",
        ["M. Fischer", "Y. Wang", "A. Petrov"],
        22,
        "q2",
        ["D1", "D2"],
        "We compare eight graph learning pipelines on three clinical prediction tasks. Performance is dominated by graph construction rather than the message-passing architecture.",
        "SCImago SJR 2025 · Q2 · Medicine",
        "journal",
    ),
    paper(
        "10.1016/j.commatsci.2026.113201",
        "Data-efficient scientific discovery with physics-informed surrogates",
        "Computational Materials Science",
        "2026-09-05",
        ["S. Novak", "T. Ali"],
        15,
        "q2",
        ["D3"],
        "A physics-informed surrogate reduces the number of expensive simulations by an order of magnitude on a materials discovery task. The paper reports negative results for two transfer settings.",
        "SCImago SJR 2025 · Q2 · Materials Science",
        "journal",
    ),
]

DATASETS = [
    {
        "doi": "10.5281/zenodo.10000001",
        "title": "MedSegBench 2026",
        "description": "Multi-centre CT and MRI segmentation benchmark with scanner metadata and external test splits.",
        "year": 2026,
        "publisher": "Zenodo",
        "license": "CC BY 4.0",
        "url": "",
        "creators": ["A. Petrova", "M. Chen"],
        "direction_ids": ["D2"],
    },
    {
        "doi": "10.5281/zenodo.10000002",
        "title": "GraphBench-Materials",
        "description": "Graph construction variants and property-prediction splits for materials discovery.",
        "year": 2026,
        "publisher": "Zenodo",
        "license": "CC0 1.0",
        "url": "",
        "creators": ["S. Novak"],
        "direction_ids": ["D1", "D3"],
    },
    {
        "doi": "10.5281/zenodo.10000003",
        "title": "MicroscopySSL-2026",
        "description": "Unlabelled and partially labelled microscopy volumes for self-supervised representation learning.",
        "year": 2026,
        "publisher": "Zenodo",
        "license": "CC BY-NC 4.0",
        "url": "",
        "creators": ["L. Moroz", "D. Williams"],
        "direction_ids": ["D2", "D3"],
    },
]

ANALYSIS = {
    "schemaVersion": 1,
    "generatedAt": "2026-11-02T12:00:00.000Z",
    "title": "Научный дайджест: graph ML и медицинские изображения",
    "summary": "За период появились три связанных сдвига: foundation-модели и self-supervised обучение для медицинских изображений, test-time adaptation и uncertainty-гарантии, а также нейрооператоры с физическими ограничениями. Датасеты становятся самостоятельным результатом: появляются многодоменные бенчмарки и наборы для graph learning.",
    "themes": [
        {
            "title": "Foundation models и self-supervised learning для медицинских изображений",
            "summary": "Основная линия — перейти от полностью размеченных датасетов к предобучению на неразмеченных объёмах и малому числу меток. Внешняя валидация и калибровка остаются слабым местом.",
            "directionIds": ["D2"],
            "confidence": "high",
            "evidence": ["10.1038/s42256-026-01001-1", "10.1016/j.media.2026.103001"],
        },
        {
            "title": "Надёжность под distribution shift",
            "summary": "Test-time adaptation и conformal prediction всё чаще рассматриваются вместе: первое снижает сдвиг, второе даёт проверяемые гарантии и помогает обнаруживать сбои.",
            "directionIds": ["D2", "D3"],
            "confidence": "medium",
            "evidence": ["10.1109/TPAMI.2026.1001", "10.5555/cvpr.2026.014"],
        },
        {
            "title": "Графовые модели: масштаб и построение графа",
            "summary": "С одной стороны, разреженные graph transformers масштабируются до больших графов; с другой — бенчмарки показывают, что качество сильнее зависит от построения графа, чем от архитектуры.",
            "directionIds": ["D1", "D2"],
            "confidence": "high",
            "evidence": ["10.5555/neurips.2026.001", "10.1016/j.jbi.2026.104501"],
        },
        {
            "title": "Physics-aware neural operators",
            "summary": "Физические ограничения и латентная динамика позволяют сократить число дорогих симуляций; перенос на новые граничные условия остаётся открытым вопросом.",
            "directionIds": ["D3"],
            "confidence": "medium",
            "evidence": ["10.5555/icml.2026.088", "10.1016/j.commatsci.2026.113201"],
        },
    ],
    "datasets": [
        {
            "doi": "10.5281/zenodo.10000001",
            "name": "MedSegBench 2026",
            "description": "Мультицентровой бенчмарк КТ/МРТ с metadata сканеров и external test splits.",
            "year": 2026,
            "license": "CC BY 4.0",
            "directionIds": ["D2"],
        },
        {
            "doi": "10.5281/zenodo.10000002",
            "name": "GraphBench-Materials",
            "description": "Варианты построения графов и split'ы для предсказания свойств материалов.",
            "year": 2026,
            "license": "CC0 1.0",
            "directionIds": ["D1", "D3"],
        },
        {
            "doi": "10.5281/zenodo.10000003",
            "name": "MicroscopySSL-2026",
            "description": "Неразмеченные и частично размеченные объёмы микроскопии для self-supervised обучения.",
            "year": 2026,
            "license": "CC BY-NC 4.0",
            "directionIds": ["D2", "D3"],
        },
    ],
    "criteria": {
        "a_star": [
            "Конференция имеет действующий ранг A* в ICORE/CORE для указанного года.",
            "Работа — полноценная рецензируемая публикация, а не тезис, постер или препринт.",
            "Дата публикации входит в выбранный период.",
            "Тема и площадка совпадают с направлением; название/акроним подтверждены кэшем ICORE.",
        ],
        "q1": [
            "Журнал входит в Q1 по SJR в релевантной предметной категории и году.",
            "Работа — article/review, прошла рецензирование, имеет DOI и полные метаданные.",
            "Дата публикации входит в выбранный период.",
            "Квартиль относится к журналу, а не к конкретной статье.",
        ],
        "q2": [
            "Журнал входит в Q2 по SJR в релевантной предметной категории и году.",
            "Работа — article/review, прошла рецензирование, имеет DOI и полные метаданные.",
            "Дата публикации входит в выбранный период.",
            "Q2 — не автоматически «слабее»: это другой квартиль и профиль риска.",
        ],
        "study": [
            "Peer-reviewed venue, не препринт и не редакционная заметка.",
            "DOI разрешается и совпадает с метаданными OpenAlex/Crossref.",
            "Тема релевантна одному из сохранённых направлений.",
            "Нет признаков retraction, если поле доступно.",
            "Аннотации достаточно для синтеза; full text не читался.",
            "Код и датасет — плюс, но не обязательное условие.",
        ],
        "caveats": [
            "Ранг площадки — фильтр, а не доказательство качества статьи.",
            "Один журнал может быть Q1 в одной категории и Q2 в другой.",
            "OpenAlex и DataCite могут пропускать записи.",
            "Синтез основан на аннотациях и метаданных.",
        ],
        "tracks": [
            {
                "directionId": "D1",
                "track": "Foundation models для биомедицинских изображений",
                "venue": "Q1 journal или A* (NeurIPS / CVPR / KDD)",
                "baselines": ["nnU-Net / U-Net", "BiomedCLIP / FetalCLIP", "MedSAM", "linear probe и full fine-tuning"],
                "newDatasets": ["MedSegBench 2026", "GraphBench-Materials (для graph-ветки)"],
                "validation": [
                    "внешний test set, не использованный в pretraining",
                    "zero-shot и few-shot 1/5/10%",
                    "калибровка и subgroup analysis по центру/модальности",
                    "сравнение compute и parameters при равном бюджете",
                ],
                "ablations": ["pretraining corpus", "language supervision", "PEFT vs full FT"],
                "reproducible": ["код и чекпойнты", "точные split'ы", "лицензии данных"],
            },
            {
                "directionId": "D2",
                "track": "Сегментация медицинских изображений",
                "venue": "Q1 journal (TMI, MedIA, TPAMI) или A* (CVPR / MICCAI)",
                "baselines": ["nnU-Net", "U-Net", "SwinUNETR", "SAM / MedSAM", "M2SNet"],
                "newDatasets": ["MedSegBench 2026", "SynAPSeg"],
                "validation": [
                    "внешний test set на новом датасете",
                    "cross-centre и low-label regime",
                    "Dice, HD95, ASD и калибровка",
                    "анализ failure cases и boundary errors",
                ],
                "ablations": ["encoder", "prompt strategy", "semi-supervision", "uncertainty head"],
                "reproducible": ["код и веса", "split'ы", "версия датасета"],
            },
            {
                "directionId": "D3",
                "track": "Морфология шипиков и нейронная активность",
                "venue": "Q1 journal (Neuron, J Neurosci, Bioinformatics) или A* (MICCAI)",
                "baselines": ["SpineTool", "3D shape descriptors", "ручная морфометрия / Fiji", "CNN или transformer baseline"],
                "newDatasets": ["MicroscopySSL-2026", "SynAPSeg (synapse detection)"],
                "validation": [
                    "независимые животные/нейроны и новый микроскопный протокол",
                    "blinded manual validation",
                    "test-retest и effect size с CI",
                    "перенос на Alzheimer/контроль",
                ],
                "ablations": ["descriptors", "normalization", "augmentation", "segmentation backbone"],
                "reproducible": ["код", "параметры микроскопии", "raw data или accession"],
            },
        ],
    },
    "ranking_notes": [
        "Q1/Q2 — квартиль SJR 2025 в указанной категории; A* — ICORE2026.",
        "Пример синтетический: DOI и названия не являются реальными публикациями.",
    ],
    "warnings": ["Демонстрационные данные: названия и DOI синтетические, не являются реальными публикациями."],
}


def main() -> int:
    EXAMPLES.mkdir(parents=True, exist_ok=True)
    candidates = {
        "schemaVersion": 1,
        "generatedAt": "2026-11-02T11:55:00.000Z",
        "period": {"from": "2026-05-02", "to": "2026-11-02"},
        "profile": PROFILE,
        "queries": [
            {"direction_id": "D1", "query": "graph neural networks", "source": "OpenAlex"},
            {"direction_id": "D2", "query": "medical image segmentation", "source": "OpenAlex"},
            {"direction_id": "D3", "query": "scientific machine learning", "source": "OpenAlex"},
            {"direction_id": "D1", "query": "graph neural networks", "source": "DataCite"},
            {"direction_id": "D2", "query": "medical image segmentation", "source": "DataCite"},
            {"direction_id": "D3", "query": "scientific machine learning", "source": "DataCite"},
        ],
        "ranking": {
            "sjr": "",
            "core": "",
            "note": "Демо: Q1/Q2 по SJR 2025, A* по ICORE2026; данные синтетические.",
        },
        "papers": PAPERS,
        "datasets": DATASETS,
        "warnings": ["Демонстрационные данные: названия и DOI синтетические, не являются реальными публикациями."],
    }
    (EXAMPLES / "example-candidates.json").write_text(
        json.dumps(candidates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (EXAMPLES / "example-analysis.json").write_text(
        json.dumps(ANALYSIS, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("wrote examples/example-candidates.json and examples/example-analysis.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())