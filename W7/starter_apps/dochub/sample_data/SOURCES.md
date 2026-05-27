# DocHub sample data — Sources & Citations

## Provenance

All 6 sample contracts in this directory are **assembled from real contract provisions** sourced from HuggingFace via:

```bash
python3 tooling/fetch_w7_datasets.py --app dochub
```

Each contract document is composed of multiple real provisions (clauses) sampled from LEDGAR — clauses are grouped by clause type to form a coherent contract-like document (e.g., Master Services Agreement contains real `Services`, `Payments`, `Warranties`, `Indemnifications`, `Termination` provisions found in SEC filings).

| File | Contract template | Tenant | Composed from clause types |
|------|-------------------|--------|----------------------------|
| `tenant-acme__agreement__master_services_agreement.txt` | Master Services Agreement | tenant-acme | Services, Payments, Warranties, Indemnifications, Termination, Confidentiality, Governing Law, Notices, Counterparts, Severability |
| `tenant-globex__nda__non_disclosure_agreement.txt` | Non-Disclosure Agreement | tenant-globex | Confidentiality, Definitions, Use Of Proceeds, Notices, Governing Law, Counterparts, Severability, Waivers |
| `tenant-initech__license__software_license.txt` | Software License | tenant-initech | Warranties, Indemnifications, Restrictions, Intellectual Property, Termination, Disclaimers, Limitations Of Liability, Governing Law |
| `tenant-acme__agreement__employment_agreement.txt` | Employment Agreement | tenant-acme | Compensation, Benefits, Confidentiality, Non-Compete, Termination, Governing Law, Indemnifications, Notices |
| `tenant-globex__contract__sales_purchase_agreement.txt` | Sales & Purchase Agreement | tenant-globex | Closings, Payments, Warranties, Indemnifications, Releases, Governing Law, Notices, Counterparts, Severability |
| `tenant-initech__addendum__data_processing_addendum.txt` | Data Processing Addendum | tenant-initech | Confidentiality, Indemnifications, Notices, Termination, Governing Law, Severability, Definitions |

`manifest.json` maps tenants → files.

## HuggingFace dataset

- **Name:** `coastalcph/lex_glue`
- **Config:** `ledgar` (LEDGAR: Labeled EDGAR contract provisions)
- **URL:** https://huggingface.co/datasets/coastalcph/lex_glue
- **Schema:** columns `text` (provision text), `label` (provision type, 100 categories)
- **Size:** 60K train + 10K validation + 10K test provisions

## Source corpus

LEDGAR provisions come from **real public SEC EDGAR filings** (US Securities & Exchange Commission) — contracts attached to 10-K, 10-Q, 8-K, and S-1 filings of US public companies. These are public-domain government records but the dataset publisher (LEDGAR / lex_glue) applies its own license terms to the curated/labeled dataset.

## License

The `lex_glue` benchmark dataset is licensed under **CC-BY-4.0** (Creative Commons Attribution 4.0).
- License: https://creativecommons.org/licenses/by/4.0/
- Terms: free to share + adapt for any purpose, including commercial, with attribution

## Attribution

When using or redistributing these files (or derivatives), cite both the LEDGAR paper and the lex_glue benchmark:

> Tuggener, D., von Däniken, P., Peetz, T., & Cieliebak, M. (2020). LEDGAR: A Large-Scale Multi-label Corpus for Text Classification of Legal Provisions in Contracts. In *Proceedings of the 12th Language Resources and Evaluation Conference (LREC 2020)*, pages 1235–1241.

> Chalkidis, I., Jana, A., Hartung, D., Bommarito, M., Androutsopoulos, I., Katz, D. M., & Aletras, N. (2022). LexGLUE: A Benchmark Dataset for Legal Language Understanding in English. In *Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics (ACL 2022)*.

## BibTeX

```bibtex
@inproceedings{tuggener2020ledgar,
  title       = {{LEDGAR}: A Large-Scale Multi-label Corpus for Text Classification of Legal Provisions in Contracts},
  author      = {Tuggener, Don and von D{\"a}niken, Pius and Peetz, Thomas and Cieliebak, Mark},
  booktitle   = {Proceedings of the 12th Language Resources and Evaluation Conference (LREC 2020)},
  pages       = {1235--1241},
  year        = {2020},
  publisher   = {European Language Resources Association},
  url         = {https://aclanthology.org/2020.lrec-1.155/}
}

@inproceedings{chalkidis2022lexglue,
  title       = {{LexGLUE}: A Benchmark Dataset for Legal Language Understanding in {English}},
  author      = {Chalkidis, Ilias and Jana, Abhik and Hartung, Dirk and Bommarito, Michael and Androutsopoulos, Ion and Katz, Daniel Martin and Aletras, Nikolaos},
  booktitle   = {Proceedings of the 60th Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)},
  pages       = {4310--4330},
  year        = {2022},
  publisher   = {Association for Computational Linguistics},
  url         = {https://aclanthology.org/2022.acl-long.297/}
}
```

## Re-generate

To replace these samples with different contract templates:

1. Edit `tooling/fetch_w7_datasets.py` → `LEDGAR_CONTRACT_TEMPLATES` list
2. Run `python3 tooling/fetch_w7_datasets.py --app dochub`
