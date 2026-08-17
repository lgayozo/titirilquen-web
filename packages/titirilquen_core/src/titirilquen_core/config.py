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

ModoElegido = Literal["Auto", "Metro", "Bici", "Caminata", "Teletrabajo"]
"""Lo que un agente termina teniendo asignado. A diferencia de `Modo`, incluye
el teletrabajo; y donde se usa admite `None`, para el agente varado — aquel al
que ningún modo le resultó factible."""


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
    # ACCESO caminando a la estación de metro. Separado de `b_tiempo_caminata`
    # en ago-2026: un solo coeficiente pesaba las dos cosas, y no son lo mismo.
    #
    # Este SÍ tiene valor de norma: Precios Sociales 2026 del SNI, Tabla 2.1,
    # asigna ponderador 2 a la caminata frente a 1 del viaje en vehículo, y acota
    # que esos valores aplican «solo para los usuarios de transporte público
    # mayor» y que en viajes combinados «solo el tramo de transporte público está
    # afecto a ellos» — o sea, exactamente este término. De ahí el 2.0 x
    # `b_tiempo_viaje`.
    b_tiempo_acceso: float
    # Modo CAMINATA completo (el viaje entero a pie). NO está cubierto por la
    # tabla del SNI, que habla del tramo caminado de un viaje en transporte
    # público. Queda en 1.7 x `b_tiempo_viaje`, que es un juicio, no una norma:
    # caminar todo el viaje es un modo elegido, no un tramo forzado de otro.
    b_tiempo_caminata: float
    penalizaciones_fisicas: PhysicalPenalties


class StratumConfig(BaseModel):
    """Configuración por estrato: quién es y cómo valora el viaje.

    Tuvo también `prob_jornada_flexible`, `prob_part_time` y una `jornada` con
    horas por tipo de contrato. Se retiraron en la limpieza de agosto de 2026:
    ningún módulo del núcleo los leía (D-07 ya lo declaraba: "sólo afectan
    metadatos de agentes"), y ni siquiera eso — `Agente` no tiene campos de
    jornada. Eran ocho números por estrato que el frontend mostraba y nadie
    usaba. Si algún día la jornada entra al modelo, entra con su ecuación.
    """

    model_config = ConfigDict(extra="forbid")

    prob_teletrabajo: float = Field(ge=0, le=1)
    prob_auto: float = Field(ge=0, le=1)
    betas: StratumBetas


class GlobalConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    v_auto: float = 31
    v_metro: float = 35
    v_bici: float = 14
    v_caminata: float = 4.8
    costo_combustible_km: float = 120
    costo_tarifa_metro: float = 800
    # 2000 (antes 4000, antes 6000). NO es un precio de lista: el modelo le cobra
    # parking a TODOS los viajes en auto, cuando en la realidad buena parte
    # estaciona gratis (en la calle o provisto por el empleador). O sea es un
    # costo ESPERADO = precio x probabilidad de pagarlo.
    #
    # Bajo de 4000 al recalibrar el valor del tiempo (ago-2026): 4000 se habia
    # elegido cuando `b_costo` era 6.7x menor y valia 5.8 minutos del tiempo del
    # estrato alto; con el VoT corregido (6.200 $/h) pasaba a valer 39 y hundia
    # el auto a 5.7% con el corredor descongestionado (v/c 0.47). Con 2000 el
    # reparto vuelve a 12.7% y el v/c a 1.03, la rodilla de la BPR.
    #
    # Como hay un UNICO `b_costo` que aplica a la suma de todo el dinero, la
    # razon entre las elasticidades de parking, bencina y tarifa la fijan los
    # MONTOS, no los betas — ver scripts/diagnostico_elasticidades.py.
    costo_parking: float = 2000
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
    # (0.20, 0.50, 0.30) — antes (0.10, 0.40, 0.50). Con media ciudad en el
    # estrato bajo (VoT $1.600/h), los ~$1.800 de diferencia entre auto y metro
    # les valen 67 minutos y el auto no puede competir por construcción: era una
    # ciudad pobre por supuesto, no por resultado. Ago-2026.
    share_estratos: tuple[float, float, float] = Field(default=(0.20, 0.50, 0.30))
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
    # 1000 (antes 300): capacidad realista de un tren de metro. Ademas de
    # realismo, pone al metro en la zona EMPINADA de su economia de escala
    # (f_op = carga/K queda en ~5-7 tph, espera ~4-6 min): ahi las palancas del
    # metro muerden y la paradoja de Downs-Thomson es observable bajo Wardrop
    # (ver scripts/buscar_downs_thomson.py y docs/informe-downs-thomson.html).
    # Con 300 la frecuencia era ~21 tph y la espera 1.4 min: curva plana, metro
    # insensible a todo.
    capacidad_tren: int = 1000
    num_estaciones: int = Field(default=10, ge=2)
    v_caminata_kmh: float = 4.8
    # PROVISORIO — pendiente de fuente. Costo de operación por tren-km ($), con
    # tren-km/h = f_op · largo de línea · 2 (misma definición que usa
    # `emissions.py`). Habilita el costo del operador, el subsidio
    # (= costo − recaudación por tarifa) y la pregunta de autofinanciamiento.
    #
    # OJO al interpretarlo: este modelo representa SOLO la hora punta, sin valle
    # ni recorridos en vacío, así que su carga por tren-km es varias veces la de
    # un sistema real. Con un valor por tren-km realista, el metro del modelo
    # sale holgadamente superavitario — y eso es un artefacto del alcance, no un
    # resultado. Ver docs/CONTINUAR.md.
    costo_operacion_tren_km: float = Field(default=12000, ge=0)
    # Factor DÍA/PUNTA para que el subsidio y el autofinanciamiento signifiquen
    # algo. El autofinanciamiento compara costo DIARIO contra ingreso DIARIO,
    # pero este modelo entrega solo la hora punta. Escalando:
    #
    #   autofinancia  <=>  costo_punta · (R_costo / R_ingreso) <= ingreso_punta
    #
    # con R_costo = tren-km del día / tren-km de la punta y R_ingreso = viajes
    # del día / viajes de la punta. Como el servicio fuera de punta circula más
    # vacío, R_costo > R_ingreso y el factor es > 1. En una sola frase: cuánto
    # más caro sale operar el día completo, POR VIAJE, que si todo el día
    # tuviera la carga de la punta.
    #
    # 2.0 es un orden de magnitud razonable (la punta concentra ~10-12% de los
    # viajes del día mientras el servicio corre ~18 h), pero es PROVISORIO como
    # el costo por tren-km. Con los defaults el metro igual sale superavitario:
    # haría falta ~3.7 para que requiera subsidio. La diferencia restante no es
    # del factor sino de dos rasgos del modelo — los viajes son cortos (~5 km en
    # una ciudad de 20, porque la demanda se concentra junto al CBD) y la tarifa
    # es plana, así que el ingreso por pax-km sale alto. Ver docs/CONTINUAR.md.
    factor_dia_punta: float = Field(default=2.0, gt=0)
    # Detención en cada estación INTERMEDIA entre la de subida y el CBD. Sin
    # esto, agregar estaciones acortaba el acceso a caminar SIN ningún costo en
    # tiempo de viaje: un almuerzo gratis que hacía monótonamente buena la
    # densificación de la red. Con la detención aparece el trade-off real —más
    # estaciones = menos acceso pero más viaje— que es el fenómeno que se quiere
    # enseñar. 0.5 min = 30 s por parada.
    #
    # Es una detención FIJA. Un dwell que crezca con los pasajeros que suben
    # sería una DESECONOMÍA
    # de escala del metro, que juega en contra del efecto Möhring; es una
    # decisión de modelación aparte, no un simple refinamiento.
    tiempo_detencion_min: float = Field(default=0.5, ge=0)
    # 2 (antes 6): con K=1000 la frecuencia demandada queda en ~5-7 tph, y un
    # piso de 6 la dejaria RECORTADA justo donde vive el efecto Mohring — al
    # perder pasajeros la frecuencia no podria caer y el metro seria insensible.
    # El piso de 2 (intervalo maximo 30 min) solo actua como resguardo extremo.
    frec_min: float = 2
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
        description=(
            "α de la BPR de congestión de andén: t_espera = base·(1 + α·ρ^β), "
            "ρ = carga/(frec_max·K)"
        ),
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
    assignment: Literal["montecarlo", "expected", "todo_o_nada"] = Field(
        default="montecarlo",
        description=(
            "Método de asignación de demanda. 'montecarlo' sortea el modo de cada "
            "agente; 'expected' usa los flujos esperados = probabilidades logit "
            "(el mismo modelo sin ruido de muestreo); 'todo_o_nada' manda al "
            "grupo ENTERO al modo de mayor utilidad. "
            "Los tres son el mismo modelo de utilidad aleatoria: 'todo_o_nada' es "
            "el límite del logit cuando la escala de los coeficientes crece, o sea "
            "con varianza cero en la parte no observada. "
            "NO produce igualación de costos entre modos — medido en "
            "scripts/auditoria_wardrop.py: los cuatro modos se usan a la vez con "
            "costos que difieren hasta 32 min. Lo que cambia es que el grupo "
            "marginal salta entero en vez de trasvasar una fracción, y de ahí que "
            "sólo con este método aparezca Downs-Thomson (docs/CONTINUAR.md §5). "
            "Se llamó 'wardrop' hasta agosto de 2026; el nombre prometía una "
            "condición de equilibrio de usuario que este modelo no cumple."
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
