# titirilquen_core

Núcleo científico del simulador Titirilquen. Paquete Python puro (sin UI, sin web) que corre tanto en FastAPI como en Pyodide.

## Instalación

```bash
pip install -e ".[dev]"
pytest
```

## Uso mínimo

```python
from titirilquen_core import (
    CityConfig, DemandConfig, SimulationConfig, SupplyConfig, run_msa,
)
from titirilquen_core.presets import DEFAULT_STRATA

sim = SimulationConfig(
    city=CityConfig(n_celdas=1001, largo_ciudad_km=20, densidad_por_celda=100),
    supply=SupplyConfig(),
    demand=DemandConfig.model_validate({"estratos": DEFAULT_STRATA}),
    max_iter=12,
    seed=42,
)
trace = run_msa(sim)

last = trace.iteraciones[-1]
print(last.modal_split)
```

## Módulos

```
titirilquen_core/
├── city.py                     CiudadLineal (1D con CBD al centro)
├── config.py                   Esquemas Pydantic (fuente única)
├── population.py               Generador de agentes sintéticos
├── presets.py                  Presets de ciudad y políticas
├── emissions.py                CO₂ por velocidad local
├── supply/
│   ├── bike.py                 BPR + pendiente
│   ├── car.py                  Greenshields + BPR
│   └── train.py                Sistema cíclico + freq. endógena
├── demand/
│   ├── utility.py              Utilidades logit + breakdown
│   └── choice.py               Logit multinomial
└── equilibrium/
    └── msa.py                  MSA + streaming iter_msa()
```

## Correspondencia con el repo original

Este paquete es el refactor de `titirilquen-repo/app.py` (oferta, demanda, MSA, emisiones) y parcialmente de `titirilquen-repo/Ciudad2.py` (land use queda para v2). Las divergencias con el Overleaf se documentan en `../../docs/DISCREPANCIES.md`.
