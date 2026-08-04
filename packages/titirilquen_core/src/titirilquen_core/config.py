"""Esquemas Pydantic — fuente única de configuración para el simulador.

Reemplaza el dict `CONFIG_DEMANDA` duplicado entre `app.py` y `Ciudad2.py` del
repositorio original. Todos los valores por defecto coinciden con los del
código original para preservar compatibilidad.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

StratumId = Literal[1, 2, 3]
"""1 = Alto, 2 = Medio, 3 = Bajo."""

Modo = Literal["Auto", "Metro", "Bici", "Caminata"]
"""Modos de transporte que el usuario puede habilitar/deshabilitar en el set de
elección antes de correr el equilibrio. El teletrabajo no es un modo elegible:
se decide antes (prob_teletrabajo) y no se ve afectado por esta selección."""


class PhysicalPenalties(BaseModel):
    """Penalizaciones aditivas escalonadas (step) para bici y caminata.

    Ver docs/DISCREPANCIES.md (D-02) — estas son constantes aditivas, no
    multiplicativas como sugiere el Overleaf.
    """

    model_config = ConfigDict(extra="forbid")

    bici_10: float
    bici_20: float
    bici_30: float
    walk_5: float
    walk_15: float
    walk_25: float


class StratumBetas(BaseModel):
    """Coeficientes del logit multinomial por estrato."""

    model_config = ConfigDict(extra="forbid")

    asc_auto: float
    asc_metro: float
    asc_bici: float
    asc_caminata: float
    b_tiempo_viaje: float
    b_costo: float
    b_tiempo_espera: float
    b_tiempo_caminata: float
    penalizaciones_fisicas: PhysicalPenalties


class JornadaHoras(BaseModel):
    model_config = ConfigDict(extra="forbid")

    horas_rigido: float = 9.0
    horas_flexible: float = 8.0
    horas_part_time: float = 4.0


class StratumConfig(BaseModel):
    """Configuración por estrato. Inactiva por defecto: jornada/part_time sólo afectan
    metadatos de agentes, no la utilidad (ver D-07)."""

    model_config = ConfigDict(extra="forbid")

    prob_teletrabajo: float = Field(ge=0, le=1)
    prob_auto: float = Field(ge=0, le=1)
    prob_jornada_flexible: float = Field(default=0.3, ge=0, le=1)
    prob_part_time: float = Field(default=0.1, ge=0, le=1)
    jornada: JornadaHoras = Field(default_factory=JornadaHoras)
    betas: StratumBetas


class GlobalConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    v_auto: float = 31
    v_metro: float = 35
    v_bici: float = 14
    v_caminata: float = 4.8
    costo_combustible_km: float = 120
    costo_tarifa_metro: float = 800
    # 4000 (antes 6000): con 6000 el parking era ~91% del costo monetario del
    # viaje en auto a la distancia media, y su elasticidad salia -0.588 mientras
    # bencina y tarifa quedaban en -0.03. Como hay un UNICO `b_costo` que aplica
    # a la suma de todo el dinero, la razon entre esas elasticidades la fijan los
    # MONTOS, no los betas — ver scripts/diagnostico_elasticidades.py.
    costo_parking: float = 4000
    # Multiplicador ADIMENSIONAL sobre la curva COPERT de emision del auto
    # (`emissions.factor_emision_auto(v)`), para representar la composicion de
    # la flota: 1.0 = flota de referencia, ~0.7 hibrida, ~0.15 electrica.
    #
    # Reemplaza al antiguo `factor_emision_auto = 0.180`, que era un parametro
    # HUERFANO: nadie lo leia. Por eso el preset «Vehiculos hibridos» solo
    # abarataba la bencina y terminaba SUBIENDO el CO2 (mas viajes en auto, la
    # misma emision por km). Se multiplica en vez de reemplazar la curva para
    # conservar la dependencia de la velocidad, que es lo pedagogicamente
    # valioso: congestion => menos velocidad => mas emision por km.
    factor_flota_auto: float = Field(default=1.0, gt=0)
    # kg CO₂ por tren-km (D-29): el metro emite por servicio circulando, no por
    # pasajero. 2.5 ≈ continuidad con la calibración anterior (0.040 kg/pax·km)
    # en el escenario de referencia, y plausible para metro eléctrico
    # (~8 kWh/km × ~0.3 kgCO₂/kWh). El frontend migra configs viejas.
    factor_emision_metro_tren_km: float = 2.5


class DemandConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    globales: GlobalConfig = Field(default_factory=GlobalConfig)
    estratos: dict[StratumId, StratumConfig]

    @field_validator("estratos", mode="before")
    @classmethod
    def _coerce_keys(cls, v: object) -> object:
        """JSON dict keys llegan como str; convertir a int para casar con `StratumId`."""
        if isinstance(v, dict):
            return {int(k) if isinstance(k, str) else k: val for k, val in v.items()}
        return v

    @field_validator("estratos")
    @classmethod
    def _check_strata_complete(
        cls, v: dict[StratumId, StratumConfig]
    ) -> dict[StratumId, StratumConfig]:
        missing = {1, 2, 3} - set(v.keys())
        if missing:
            raise ValueError(f"Faltan estratos: {sorted(missing)}")
        return v


class CityConfig(BaseModel):
    """Ciudad lineal. `n_celdas` debe ser impar para que el CBD quede centrado."""

    model_config = ConfigDict(extra="forbid")

    n_celdas: int = Field(default=1001, ge=11)
    largo_ciudad_km: float = Field(default=20.0, gt=0)
    # Densidad FÍSICA (D-28): población total = densidad_hab_km · largo, así que
    # `n_celdas` queda como variable puramente numérica (antes era hab/celda y
    # refinar la grilla multiplicaba la población). 500 hab/km ≈ 50 hogares por
    # cuadra de 100 m. El frontend migra configs viejas (serialization.ts).
    densidad_hab_km: float = Field(default=500.0, gt=0)
    pendiente_porcentaje: float = Field(default=0.0)
    teletrabajo_factor: float = Field(default=1.0, ge=0.0, le=5.0)
    share_estratos: tuple[float, float, float] = Field(default=(0.10, 0.40, 0.50))
    # `ingresos_estratos` se eliminó (jun-2026): nunca se usó en el core y
    # duplicaba el `y` del módulo de suelo. El frontend descarta el campo al
    # importar escenarios viejos (ver serialization.ts::migrateConfig).

    @field_validator("share_estratos")
    @classmethod
    def _shares_sum_to_one(cls, v: tuple[float, float, float]) -> tuple[float, float, float]:
        if abs(sum(v) - 1.0) > 1e-6:
            raise ValueError(f"Los shares de estratos deben sumar 1, obtuve {sum(v)}")
        return v


class BikeSupplyParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    v_media_kmh: float = 14
    # 2500 bici/h = flujo de saturacion realista de una ciclovia. Antes 800, que
    # dejaba el modo operando a v/c ~2.4, POR ENCIMA del techo de caminata (que
    # se activa sobre v/c = ((v_bici/v_caminata - 1)/alpha)^(1/beta) = 1.96): en
    # esa zona la BPR ya no opera y alpha/beta no significan nada.
    capacidad_pista: int = 2500
    alpha_bpr: float = 0.5
    beta_bpr: float = 2.0


class CarSupplyParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    v_max_kmh: float = 31
    ancho_pista_m: float = 3.5
    largo_vehiculo_m: float = 5.0
    gap_m: float = 2.0
    # 2 pistas => v/c ~1.05 en la ciudad de referencia. Se probo con 3 (v/c
    # 0.71) y la oferta vial quedaba MUERTA como palanca: bajo capacidad la BPR
    # es plana, asi que de 3 a 6 pistas el reparto se movia 0.11 pp. Todo el
    # efecto vive cerca de v/c = 1. No se puede tener a la vez una ciudad base
    # descongestionada y una oferta vial que mueva el reparto.
    num_pistas: int = Field(default=2, ge=1)
    alpha_bpr: float = 0.8
    beta_bpr: float = 2.0
    # Capacidad por pista (veh/h). None ⇒ Greenshields q_max = k_j·v_l/4, que
    # ACOPLA capacidad y velocidad (subir v_max sube C en igual proporción y la
    # velocidad nunca puede empeorar la congestión). Un valor explícito separa
    # C de v_f como en la BPR estándar — ver docs/ANALISIS_SENSIBILIDAD.md S-04.
    capacidad_pista: float | None = Field(default=None, gt=0)


class TrainSupplyParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    v_tren_kmh: float = 35
    # Capacidad por tren a la escala de demanda del modelo. Calibrada para que la
    # frecuencia endógena f_op = clip(carga_pico/cap_tren, f_min, f_max) sea
    # responsiva en el rango de uso (antes 1200 dejaba f clavada en f_min y el
    # efecto Möhring inactivo — ver docs/VERIFICACION_TRANSPORTE.md, H1).
    capacidad_tren: int = 300
    num_estaciones: int = Field(default=10, ge=2)
    v_caminata_kmh: float = 4.8
    tasa_carga: float = 6.0
    # Rango de frecuencia operativa (trenes/h). Valores realistas de metro:
    # frec_min≈6 ⇒ ~10 min de intervalo (valle); frec_max≈30 ⇒ ~2 min (punta).
    # El rango amplio fortalece el efecto Mohring: al perder demanda la
    # frecuencia cae más y la espera (=30/f) sube con pendiente -30/f^2, más
    # pronunciada a baja frecuencia. Ver docs/DISCREPANCIES.md (D-18).
    frec_min: float = 6
    # 40 (antes 30): con 30 la frecuencia demandada quedaba justo en el tope,
    # asi que f_op estaba RECORTADA y el efecto Mohring agotado en el default
    # (mas demanda ya no traia mas trenes). Con 40 la frecuencia queda interior
    # y vuelve a responder a la demanda. Ojo: por encima de la frecuencia que
    # pide la demanda, subir este tope no hace NADA — el indicador de la UI lo
    # dice explicitamente (AT-08).
    frec_max: float = 40
    anden_alpha: float = Field(
        default=0.5,
        ge=0,
        description="α de la BPR de congestión de andén: t_espera = base·(1 + α·ρ^β), ρ = carga/(frec_max·K)",
    )
    anden_beta: float = Field(default=4.0, ge=0, description="β de la BPR de congestión de andén")


class SupplyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bike: BikeSupplyParams = Field(default_factory=BikeSupplyParams)
    car: CarSupplyParams = Field(default_factory=CarSupplyParams)
    train: TrainSupplyParams = Field(default_factory=TrainSupplyParams)


class SimulationConfig(BaseModel):
    """Configuración completa de una corrida del simulador — el objeto que se
    serializa al archivo `.ttrq.json`."""

    model_config = ConfigDict(extra="forbid")

    city: CityConfig = Field(default_factory=CityConfig)
    supply: SupplyConfig = Field(default_factory=SupplyConfig)
    demand: DemandConfig
    # 20 (no 12): con tolerance>0 el corte es por residual; el margen extra deja
    # converger la cola lenta ~1/it del MSA en escenarios rígidos (ver D-21/H4).
    max_iter: int = Field(default=20, ge=1, le=100)
    # 0.1 min (antes 0.0): con 0 el criterio por residual NUNCA se cumple, asi
    # que la corrida agotaba max_iter y quedaba marcada «sin converger» aunque
    # el residuo fuera despreciable. El 0 venia de replicar el original, que
    # cortaba solo por max_iter; el costo era una etiqueta falsa. Ahora el core
    # y el frontend usan el mismo valor (se elimino la divergencia declarada del
    # contrato). `tolerance=0` sigue siendo valido y significa «no cortar por
    # residual».
    tolerance: float = Field(default=0.1, ge=0)
    seed: int | None = None
    assignment: Literal["montecarlo", "expected"] = Field(
        default="montecarlo",
        description=(
            "Método de asignación de demanda: 'montecarlo' sortea el modo de cada "
            "agente (estocástico); 'expected' usa los flujos esperados = "
            "probabilidades logit (determinista, sin ruido entre iteraciones)."
        ),
    )
    modos_habilitados: tuple[Modo, ...] = Field(
        default=("Auto", "Metro", "Bici", "Caminata"),
        description=(
            "Modos disponibles en el set de elección. Los modos excluidos se "
            "tratan como infeasibles (utilidad −∞) y no reciben demanda. Útil "
            "para escenarios estilizados (p.ej. solo Auto vs Metro)."
        ),
    )

    @field_validator("modos_habilitados")
    @classmethod
    def _at_least_one_mode(cls, v: tuple[Modo, ...]) -> tuple[Modo, ...]:
        uniq = tuple(dict.fromkeys(v))  # dedup preservando orden
        if not uniq:
            raise ValueError("Debe habilitarse al menos un modo de transporte")
        return uniq
