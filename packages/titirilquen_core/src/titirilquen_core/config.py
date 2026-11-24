"""Esquemas Pydantic — fuente única de configuración para el simulador.

Reemplaza el dict `CONFIG_DEMANDA` duplicado entre `app.py` y `Ciudad2.py` del
repositorio original. Todos los valores por defecto coinciden con los del
código original para preservar compatibilidad.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from titirilquen_core.constantes import (
    CORTE_BICI_MIN,
    CORTE_CAMINATA_MIN,
    PONDERADOR_SNI_ACCESO,
    PONDERADOR_SNI_ESPERA,
    PRECIO_MERCADO_COMBUSTIBLE_CLP_L,
    PRECIO_SOCIAL_CARBONO_CLP_T,
    PRECIO_SOCIAL_COMBUSTIBLE_AUTO_CLP_L,
    PRECIO_SOCIAL_LUBRICANTE_AUTO_CLP_L,
    PRECIO_SOCIAL_MANTENCION_CLP_H,
    PRECIO_SOCIAL_NEUMATICO_AUTO_CLP,
    PRECIO_SOCIAL_VEHICULO_AUTO_CLP,
    TASA_SOCIAL_DESCUENTO,
    VIGENCIA_PRECIOS_SOCIALES,
    VOT_SOCIAL_CLP_HORA,
)

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
    b_tiempo_viaje: float = Field(
        lt=0, description="Desutilidad del tiempo en vehículo (utiles/min); negativo"
    )
    b_costo: float = Field(
        lt=0, description="Desutilidad del dinero (utiles/$); negativo. Es λ en el suelo (D-34)"
    )
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

    v_auto: float = Field(default=31, gt=0)
    v_metro: float = Field(default=35, gt=0)
    v_bici: float = Field(default=14, gt=0)
    v_caminata: float = Field(default=4.8, gt=0)
    # Cortes de FACTIBILIDAD del conjunto de elección: sobre ese tiempo la
    # alternativa sale del set, no recibe una penalización grande. Distíngase de
    # `penalizaciones_fisicas`, que castigan progresivamente al cruzar umbrales
    # (10/20/30 min en bici, 5/15/25 a pie) pero dejan la alternativa disponible.
    #
    # Eran constantes del núcleo hasta el 2026-08-18 y se volvieron configurables
    # a pedido. El default sigue viniendo de `constantes.py` para no tener el
    # número escrito dos veces: ahí es el supuesto del modelo, acá el valor
    # inicial que el usuario puede mover.
    #
    # Ojo al moverlos: cambian el `J` del conjunto factible, y con él la brecha
    # entre logsum y utilidad máxima (docs/libro/informe-bienestar.html §4.1). Mover el
    # corte NO es una política de transporte, es un supuesto de comportamiento.
    corte_caminata_min: float = Field(default=CORTE_CAMINATA_MIN, gt=0, le=180)
    corte_bici_min: float = Field(default=CORTE_BICI_MIN, gt=0, le=180)
    # Forma de esos umbrales (oct-2026). «escalones» es la especificación
    # simplificada: penalizaciones escalonadas (D-02), cortes duros y metro
    # infactible donde la estación más cercana es la del CBD (D-69). «suaves»
    # cambia cada discontinuidad por su versión continua —rampas, corte CMNL
    # (Martínez, Aguila y Hurtubia 2009) y dominancia suave del metro frente a
    # caminar (Cascetta y Papola 2009)—, que quita los saltos del logsum y de la
    # T del suelo. Las dos usan las mismas penalizaciones y cortes; detalle en
    # demand/utility.py. Cambia la función de utilidad: no se comparan
    # bienestares entre especificaciones.
    umbrales: Literal["escalones", "suaves"] = "escalones"
    precio_combustible_clp_l: float = Field(default=PRECIO_MERCADO_COMBUSTIBLE_CLP_L, ge=0)
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
    # reparto vuelve a 12.7% y el v/c a 1.03, la rodilla de la BPR. Esas cifras
    # son de ago-2026: D5, D6 y el parking por tour las movieron, y la linea
    # base vigente esta en `tests/test_linea_base.py`.
    #
    # Como hay un UNICO `b_costo` que aplica a la suma de todo el dinero, la
    # razon entre las elasticidades de parking, bencina y tarifa la fijan los
    # MONTOS, no los betas — ver scripts/diagnostico_elasticidades.py.
    #
    # Desde oct-2026 es un costo POR DÍA (por tour casa-trabajo-casa), no por
    # viaje: se paga al llegar al trabajo y no al volver. Cada viaje de ida carga
    # `costo_parking / VIAJES_POR_TOUR` = 1000. Antes se cargaba entero en cada
    # uno de los 44 viajes del mes, o sea dos veces por día.
    costo_parking: float = 2000
    # Peaje vial por km recorrido en auto (D7, oct-2026), en $/km por viaje,
    # como la bencina pero TRANSFERENCIA: entra a la recaudación del bienestar.
    # Es la palanca que se acerca al cobro de Pigou, porque el costo externo de
    # un viaje crece con los tramos que cruza; el parking, en una ciudad donde
    # todos van al CBD, es un cobro de cordón plano. 0 = sin peaje.
    peaje_km: float = Field(default=0, ge=0)
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
    # Multiplica la probabilidad de teletrabajo de cada estrato (acotada a 1):
    # la única palanca que saca viajes de la punta. Vivía en `CityConfig` hasta
    # sep-2026, pero es gestión de demanda, no forma urbana; la interfaz ya lo
    # editaba en «Economía» desde ago-2026.
    teletrabajo_factor: float = Field(default=1.0, ge=0.0, le=5.0)


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
    """Ciudad lineal: la geometría y nada más.

    Tres números. `n_celdas` es la resolución numérica (impar, para que el CBD
    sea una celda y su centroide caiga en L/2); `largo_ciudad_km` el tamaño
    físico; `pendiente_porcentaje` el terreno, que sólo ve la bicicleta.

    Hasta sep-2026 traía además `densidad_hab_km`, `share_estratos` y
    `teletrabajo_factor`. Los dos primeros eran la fuente de población de la
    ruta «transporte solo», que dejó de existir: la población viene SIEMPRE del
    uso de suelo (`LandUseConfig.H_por_estrato` sobre la oferta `S`), así que
    eran inertes por la ruta de la app y el schema afirmaba «población =
    densidad × largo» sin condición (D-46). El tercero es una palanca de
    demanda y vive ahora en `GlobalConfig`. La densidad media es una
    CONSECUENCIA, ΣH / largo, y así se reporta."""

    model_config = ConfigDict(extra="forbid")

    n_celdas: int = Field(default=1001, ge=11)
    largo_ciudad_km: float = Field(default=20.0, gt=0)
    pendiente_porcentaje: float = Field(default=0.0)

    @field_validator("n_celdas")
    @classmethod
    def _impar(cls, v: int) -> int:
        # Con n par el centroide de la celda n//2 cae medio Δx a la derecha de
        # L/2 y la «celda del CBD» queda a esa distancia de sí misma (D-45). El
        # docstring lo exigía y ningún validador lo leía; la interfaz lo
        # forzaba por su cuenta (CityBuilder). Ahora lo exige el schema.
        if v % 2 == 0:
            raise ValueError(f"n_celdas debe ser impar para que el CBD sea una celda; obtuve {v}")
        return v


class BikeSupplyParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    v_media_kmh: float = 14
    # 6000 bici/h (oct-2026, junto con las 4 pistas de la vía): la ciclovía
    # queda a v/c ≈ 1,07 en el tramo junto al CBD, con la base de 2 pistas y
    # 4000 operaba a 1,54 (unos 6 km/h en ese tramo). Antes: 2500 (v/c 1,7, la
    # restricción que ataba la base) y 4000 (2026-09-15, v/c ≈ 1,3 al elegirse).
    # La capacidad de ciclovía es la palanca de oferta más fuerte del simulador.
    # El techo de caminata se activa sobre
    # v/c = ((v_bici/v_caminata - 1)/alpha)^(1/beta) = 1,96: por encima la BPR
    # ya no opera. Medido en docs/libro/datos/cap03.json.
    capacidad_pista: int = 6000
    alpha_bpr: float = 0.5
    beta_bpr: float = 2.0


class CarSupplyParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    v_max_kmh: float = 31
    ancho_pista_m: float = 3.5
    largo_vehiculo_m: float = 5.0
    gap_m: float = 2.0
    # 4 pistas (oct-2026). Con 2 la base cargaba el tramo junto al CBD a v/c
    # 2,01 sobre la capacidad real: la BPR multiplicaba el tiempo de ese tramo
    # por ~7 (el auto a ~4,4 km/h, más lento que caminar) y el costo externo
    # marginal ahí, t0·α·β·x^β, valía ~24 veces el tiempo a flujo libre: la
    # tarificación rendía en una zona donde la BPR ya no describe nada. Con 4,
    # v/c 1,19 (rama original; 1,15 en equilibrio).
    # Subir capacidad baja el v/c despacio porque la demanda se induce: con 3,
    # 1,54; con 5, 0,98. El techo es el codo estricto (5 pistas), descartado
    # porque ahí la oferta vial queda MUERTA como palanca: bajo capacidad la
    # BPR es plana (+1 pista: +0,17 pp de auto con 5; +0,44 con 4; +3,7 con 2).
    # No se puede tener a la vez una ciudad base descongestionada y una oferta
    # vial que mueva el reparto; 4 es el punto medio.
    num_pistas: int = Field(default=4, ge=1)
    # BPR estándar del Bureau of Public Roads (1964), la que usa la FHWA:
    # t = t0·[1 + 0,15·(v/c)^4], con c la capacidad PRÁCTICA = 0,8·C real
    # (`FACTOR_CAPACIDAD_PRACTICA`, D6): +15 % en v = 0,8·C, +37 % en v = C. Hasta
    # sep-2026 se heredaba 0,8 / 2,0 sin fuente; hasta oct-2026, c = C real.
    alpha_bpr: float = 0.15
    beta_bpr: float = 4.0
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
    # (ver scripts/buscar_downs_thomson.py y docs/libro/informe-downs-thomson.html).
    # Con 300 la frecuencia era ~21 tph y la espera 1.4 min: curva plana, metro
    # insensible a todo.
    capacidad_tren: int = 1000
    # Fija el ESPACIADO, `largo / num_estaciones`, no el conteo: las estaciones
    # van cada ese espaciado a ambos lados del CBD, CBD incluido, así que con 20
    # km y 10 resultan 11 (0, 2, …, 20). El conteo real viaja en `estaciones_km`.
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
    # algo. NO entra al bienestar social, que es de la hora punta (D12). El
    # autofinanciamiento compara costo DIARIO contra ingreso DIARIO, pero este
    # modelo entrega solo la hora punta. Escalando:
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
    # pide la demanda este tope no recorta nada (el indicador de la UI lo dice,
    # AT-08), pero SI entra en la congestion de anden: la capacidad del sistema
    # es frec_max·K (supply/train.py). Subirlo sobre 40 no mueve nada medible;
    # bajarlo cerca de la frecuencia operativa encarece la espera antes de
    # recortar (base: con 5 tph, sobre 4,1 operativos, el metro pierde 0,9 pp).
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


class PreciosSociales(BaseModel):
    """Precios sociales del Sistema Nacional de Inversiones (MDSF).

    Se publican cada año, y por eso son configuración y no constantes: se
    editan en la página Calibración y viajan con el escenario, así una corrida
    vieja se reproduce con los precios de su año. Los valores por defecto son
    los de `reference/Precios-Sociales-2026.pdf`.

    Entran sólo a la EVALUACIÓN (`bienestar.py`): costo de recursos, costo
    generalizado social y excedente con ponderación social. Ninguno toca la
    elección de modo, así que moverlos no cambia el equilibrio."""

    model_config = ConfigDict(extra="forbid")

    # Año del reporte de donde salen los valores. Sólo rotula.
    vigencia: int = Field(default=VIGENCIA_PRECIOS_SOCIALES, ge=2000, le=2100)
    # Valor social del tiempo urbano, viaje en vehículo ($/h-pasajero, tabla 2.1).
    vst_viaje_clp_h: float = Field(default=VOT_SOCIAL_CLP_HORA, ge=0)
    # Ponderadores de la tabla 2.1 sobre el tiempo en vehículo, sólo para el
    # transporte público mayor: la espera, y la caminata de acceso al metro. El
    # viaje entero a pie no está en esa tabla y pondera 1.
    ponderador_espera: float = Field(default=PONDERADOR_SNI_ESPERA, ge=0)
    ponderador_caminata: float = Field(default=PONDERADOR_SNI_ACCESO, ge=0)
    # Insumos de operación del automóvil (tablas 4.3, 4.4 y 4.5).
    combustible_auto_clp_l: float = Field(default=PRECIO_SOCIAL_COMBUSTIBLE_AUTO_CLP_L, ge=0)
    lubricante_auto_clp_l: float = Field(default=PRECIO_SOCIAL_LUBRICANTE_AUTO_CLP_L, ge=0)
    neumatico_auto_clp: float = Field(default=PRECIO_SOCIAL_NEUMATICO_AUTO_CLP, ge=0)
    vehiculo_auto_clp: float = Field(default=PRECIO_SOCIAL_VEHICULO_AUTO_CLP, ge=0)
    mantencion_clp_h: float = Field(default=PRECIO_SOCIAL_MANTENCION_CLP_H, ge=0)
    # Tasa social de descuento (tabla 1.1): anualiza la inversión.
    tasa_social_descuento: float = Field(default=TASA_SOCIAL_DESCUENTO, ge=0, le=1)
    # Precio social del carbono ($/t CO₂ equivalente, tabla 5.1).
    carbono_clp_t: float = Field(default=PRECIO_SOCIAL_CARBONO_CLP_T, ge=0)
    # Rugosidad del pavimento (IRI) con que se evalúan los «otros costos de
    # operación» del MESPIVU. NO es un precio y el manual no trae un valor por
    # defecto —lo saca de un catastro—: 0 deja sólo el término que no depende
    # de la rugosidad, o sea un piso.
    iri: float = Field(default=0, ge=0, le=20)


class Inversion(BaseModel):
    """Costos unitarios de la infraestructura, para que ampliar oferta no sea
    gratis.

    Sin esto, toda política que agrega capacidad —una pista, veinte estaciones,
    el doble de ciclovía, una flota híbrida— gana siempre: sus beneficios
    entran al costo de recursos y al bienestar, y su costo no existía.

    **Todos los costos parten en CERO** (nov-2026): no hay una fuente para
    ellos en `reference/`, y un valor plausible inventado sería peor que
    declarar el vacío. Con ceros nada cambia; se llenan en Calibración.

    Se valora el STOCK completo de cada escenario, no la diferencia contra una
    base: el nivel no significa nada por sí solo (como el del excedente), y la
    resta entre dos escenarios da la inversión adicional de uno sobre el otro,
    también cuando cambia el largo de la ciudad."""

    model_config = ConfigDict(extra="forbid")

    # $ por pista-km de vía para autos: `num_pistas × largo_ciudad_km`. Las
    # pistas del modelo son por sentido; si el costo es de la calzada completa,
    # va el de los dos sentidos.
    costo_pista_km_clp: float = Field(default=0, ge=0)
    # $ por estación de metro (las que el modelo construye, no el parámetro).
    costo_estacion_clp: float = Field(default=0, ge=0)
    # $ por km de ciclovía por cada 1.000 bici/h de capacidad: la ciclovía del
    # modelo no tiene pistas, tiene capacidad.
    costo_ciclovia_km_clp: float = Field(default=0, ge=0)
    # $ por vehículo de pasar de la flota de referencia (factor 1) a una que no
    # emite (factor 0); se aplica en proporción lineal a `1 − factor_flota_auto`
    # sobre los autos de los hogares que viajan. La proporción lineal es un
    # supuesto.
    sobrecosto_flota_limpia_clp: float = Field(default=0, ge=0)
    # Años en que se anualiza. 20 es el horizonte que el MESPIVU (5.3.8)
    # recomienda para proyectos de infraestructura.
    vida_util_anios: float = Field(default=20, gt=0, le=100)
    # Horas punta equivalentes al año: lleva el costo anual a la hora punta que
    # simula el modelo, la base del resto de los agregados. El MESPIVU (8.2.2)
    # las deriva de los flujos medidos; acá es un SUPUESTO: 250 días hábiles
    # por 2, el mismo factor día/punta del metro (`factor_dia_punta`).
    horas_punta_anio: float = Field(default=500, gt=0)


class SimulationConfig(BaseModel):
    """Configuración completa de una corrida del simulador — el objeto que se
    serializa al archivo `.ttrq.json`."""

    model_config = ConfigDict(extra="forbid")

    city: CityConfig = Field(default_factory=CityConfig)
    supply: SupplyConfig = Field(default_factory=SupplyConfig)
    demand: DemandConfig
    precios_sociales: PreciosSociales = Field(default_factory=PreciosSociales)
    inversion: Inversion = Field(default_factory=Inversion)
    # 150 (antes 40, y 20 antes de D8). Con el paso halving (auditoría B,
    # oct-2026) la base converge en 6 y el p95 del rango de la interfaz en 11.
    # El techo de 1.000 viene de cuando había métodos con paso 1/n ('montecarlo'
    # y todo o nada, retirados en nov-2026). Una corrida que converge corta
    # antes y no paga el tope.
    max_iter: int = Field(default=150, ge=1, le=1000)
    # 0,02 min sobre la brecha no amortiguada `max |c(x(t)) − t|` (D8). Con
    # 0,2 y el paso 1/n la base quedaba 0,12-0,19 pp lejos del equilibrio;
    # con halving y 0,02, la mediana de los 776 casos del rango de la interfaz
    # queda a 0,002 pp y el p95 a 0,008 (auditoría B, oct-2026).
    # `tolerance=0` sigue siendo válido y significa «no cortar por brecha».
    # Historia: el 0 original replicaba al repo de origen, que cortaba sólo por
    # max_iter y marcaba «sin converger» siempre; D8 la llevó a 0,2.
    tolerance: float = Field(default=0.02, ge=0)
    seed: int | None = None
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
