import { useCallback, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { CollapsibleSection } from "@/components/ui/CollapsibleSection";
import { EstadoPill } from "@/components/ui/EstadoPill";
import { KPIStrip, type KPI } from "@/components/ui/KPIStrip";
import { LabeledSlider } from "@/components/ui/LabeledSlider";
import { Panel } from "@/components/ui/Panel";
import { TeoriaAprendizaje } from "@/components/modules/TeoriaAprendizaje";
import { AprendizajeTrayectoria } from "@/components/viz/AprendizajeTrayectoria";
import {
  correrAprendizaje,
  correrCiudadAprendizaje,
  prepararCasoAprendizaje,
  prepararCiudadAprendizaje,
} from "@/lib/api";
import { fmtDecimal, fmtDelta } from "@/lib/modos";
import type {
  AprendizajeDict,
  CasoDict,
  CiudadDict,
  EscenarioResumenDict,
  ConfigPersona,
  StratumId,
  TiemposCeldaDict,
} from "@/lib/types";
import { useSimulationStore } from "@/store/simulationStore";

/** Bajo este margen, Φ divide por casi nada y amplifica cualquier diferencia.
 *  No es una ley: es el umbral a partir del cual la página avisa. El núcleo
 *  entrega `margen_phi` y no opina. */
const MARGEN_MINIMO = 0.05;

const CONDICIONES = ["ninguno", "ambos", "solo_mejor", "solo_peor"] as const;

export function AprendizajePage() {
  const { t } = useTranslation("simulator");

  // El caso sale del equilibrio que la app ya corrió: recalcularlo acá cuesta
  // más de un minuto en Pyodide y los tiempos por celda ya están en el trace.
  const result = useSimulationStore((s) => s.result);
  const configUsed = useSimulationStore((s) => s.configUsed);
  const landUseUsed = useSimulationStore((s) => s.landUseUsed);

  const ultima = useMemo(() => {
    const its = result?.iteraciones;
    return its && its.length > 0 ? its[its.length - 1] : null;
  }, [result]);

  const hayCorrida = Boolean(ultima && configUsed && landUseUsed);
  const nCeldas = configUsed?.city.n_celdas ?? 201;

  const [estrato, setEstrato] = useState<StratumId>(2);
  const [celda, setCelda] = useState(Math.floor(nCeldas * 0.67));
  const [d, setD] = useState(0.5);
  const [condicion, setCondicion] =
    useState<ConfigPersona["condicion"]>("ambos");
  const [sigma, setSigma] = useState(40);
  const [kShocks, setKShocks] = useState(0);
  const [delta, setDelta] = useState(0);
  const [dias, setDias] = useState(250);
  const [replicas, setReplicas] = useState(300);

  // Qué se simula: una persona con la red congelada (E1/E2) o la ciudad
  // entera con la congestión respondiendo (E3/E4).
  const [modo, setModo] = useState<"persona" | "ciudad">("persona");
  const [kModos, setKModos] = useState<2 | 3>(2);
  const [ruidoAuto, setRuidoAuto] = useState(true);
  const [ruidoMetro, setRuidoMetro] = useState(true);
  const [diasCiudad, setDiasCiudad] = useState(50);
  const [esc, setEsc] = useState<EscenarioResumenDict | null>(null);
  const [resCiudad, setResCiudad] = useState<CiudadDict | null>(null);

  const [caso, setCaso] = useState<CasoDict | null>(null);
  const [res, setRes] = useState<AprendizajeDict | null>(null);
  // La figura por defecto es el PROMEDIO de las réplicas, y eso sale suave
  // aunque cada historia sea una escalera. `vista` deja mirar una sola, e
  // `iReplica` ciclar entre ellas: la divergencia entre historias es de
  // donde viene el suavizado.
  const [vista, setVista] = useState<"promedio" | "replica">("promedio");
  const [iReplica, setIReplica] = useState(0);
  const nReplicas = res?.p_replicas?.length ?? 0;
  const [estado, setEstado] = useState<"idle" | "running" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  const correr = useCallback(async () => {
    if (!ultima || !configUsed || !landUseUsed) return;
    setEstado("running");
    setError(null);
    try {
      const tiempos: TiemposCeldaDict = {
        auto_total: ultima.t_auto[celda]!,
        bici_total: ultima.t_bici[celda]!,
        bici_libre: ultima.t_bici_libre[celda]!,
        tren_acceso: ultima.t_tren_acceso[celda]!,
        tren_espera: ultima.t_tren_espera[celda]!,
        tren_viaje: ultima.t_tren_viaje[celda]!,
      };
      const c = await prepararCasoAprendizaje({
        config: configUsed,
        land_use: landUseUsed,
        estrato,
        celda,
        tiempos,
      });
      const r = await correrAprendizaje({
        caso: c,
        aprendizaje: {
          estrato,
          celda,
          dias,
          replicas,
          semilla: 42,
          d,
          condicion: sigma > 0 ? condicion : "ninguno",
          sigma_min: condicion === "ninguno" ? 0 : sigma,
          k_shocks: delta > 0 ? kShocks : 0,
          delta_min: kShocks > 0 ? delta : 0,
        },
      });
      setCaso(c);
      setRes(r);
      setEstado("idle");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setEstado("error");
    }
  }, [
    ultima,
    configUsed,
    landUseUsed,
    estrato,
    celda,
    dias,
    replicas,
    d,
    condicion,
    sigma,
    kShocks,
    delta,
  ]);

  const correrCiudad = useCallback(async () => {
    if (!configUsed || !landUseUsed) return;
    setEstado("running");
    setError(null);
    try {
      // El escenario es el paso caro (resuelve el equilibrio, ~1 min en el
      // navegador) y se queda cacheado del lado del motor: sólo se rearma si
      // cambia la ciudad o el número de modos.
      const e =
        esc && esc.k_modos === kModos
          ? esc
          : await prepararCiudadAprendizaje({
              config: configUsed,
              land_use: landUseUsed,
              k_modos: kModos,
            });
      const r = await correrCiudadAprendizaje({
        clave: e.clave,
        ciudad: {
          k_modos: kModos,
          dias: diasCiudad,
          ultimos: Math.min(20, Math.floor(diasCiudad / 2)),
          semilla: 42,
          d,
          sigma_min: sigma,
          ruido_auto: ruidoAuto,
          ruido_metro: ruidoMetro,
          ruido_bici: false,
          escala: 1,
        },
      });
      setEsc(e);
      setResCiudad(r);
      setEstado("idle");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setEstado("error");
    }
  }, [
    configUsed,
    landUseUsed,
    esc,
    kModos,
    diasCiudad,
    d,
    sigma,
    ruidoAuto,
    ruidoMetro,
  ]);

  const margenChico = caso != null && Math.abs(caso.margen_phi) < MARGEN_MINIMO;

  const kpis: KPI[] = useMemo(() => {
    if (!caso || !res) return [];
    const largo = res.ventanas.largo;
    return [
      {
        label: t("aprendizaje.kpi.ventaja"),
        value: fmtDecimal(caso.ventaja_min, 1),
        unit: "min",
        sub: t("aprendizaje.kpi.ventaja_sub", { modo: caso.mejor }),
      },
      {
        label: t("aprendizaje.kpi.p_estrella"),
        value: fmtDecimal(caso.p_verdadera, 3),
      },
      {
        label: t("aprendizaje.kpi.phi"),
        value: fmtDecimal(largo.phi, 2),
        sub: t("aprendizaje.kpi.phi_sub", {
          desde: largo.desde,
          hasta: largo.hasta,
        }),
      },
      {
        label: t("aprendizaje.kpi.invertidos"),
        value: fmtDecimal(100 * largo.invertidos, 1),
        unit: "%",
      },
    ];
  }, [caso, res, t]);

  return (
    <div className="page">
      <aside className="sidebar">
        <div className="seg" role="group" aria-label={t("aprendizaje.modo")}>
          {(["persona", "ciudad"] as const).map((m) => (
            <button
              key={m}
              type="button"
              className={modo === m ? "active" : ""}
              onClick={() => setModo(m)}
            >
              {t(`aprendizaje.modo_${m}`)}
            </button>
          ))}
        </div>

        {modo === "ciudad" && (
          <CollapsibleSection
            title={t("aprendizaje.sec.ciudad")}
            defaultOpen
            meta={`${kModos === 2 ? "E3" : "E4"} · ${diasCiudad} d`}
          >
            <label className="flex flex-col gap-1">
              <span className="text-etiqueta text-muted">
                {t("aprendizaje.modos_ciudad")}
              </span>
              <select
                value={kModos}
                onChange={(e) =>
                  setKModos(Number(e.target.value) === 3 ? 3 : 2)
                }
              >
                <option value={2}>{t("aprendizaje.modos_dos")}</option>
                <option value={3}>{t("aprendizaje.modos_cuatro")}</option>
              </select>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={ruidoAuto}
                onChange={(e) => setRuidoAuto(e.target.checked)}
              />
              <span>{t("aprendizaje.ruido_auto")}</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={ruidoMetro}
                onChange={(e) => setRuidoMetro(e.target.checked)}
              />
              <span>{t("aprendizaje.ruido_metro")}</span>
            </label>
            <LabeledSlider
              label={t("aprendizaje.dias")}
              value={diasCiudad}
              min={20}
              max={120}
              step={5}
              onChange={setDiasCiudad}
              hint={t("aprendizaje.dias_ciudad_hint")}
            />
          </CollapsibleSection>
        )}

        {modo === "persona" && (
          <CollapsibleSection
            title={t("aprendizaje.sec.persona")}
            defaultOpen
            meta={`${t("aprendizaje.estrato")} ${estrato}`}
          >
            <label className="flex flex-col gap-1">
              <span className="text-etiqueta text-muted">
                {t("aprendizaje.estrato")}
              </span>
              <select
                value={estrato}
                onChange={(e) =>
                  setEstrato(Number(e.target.value) as StratumId)
                }
              >
                <option value={1}>1</option>
                <option value={2}>2</option>
                <option value={3}>3</option>
              </select>
            </label>
            <LabeledSlider
              label={t("aprendizaje.celda")}
              value={celda}
              min={0}
              max={nCeldas - 1}
              step={1}
              onChange={setCelda}
              hint={t("aprendizaje.celda_hint")}
            />
          </CollapsibleSection>
        )}

        <CollapsibleSection
          title={t("aprendizaje.sec.memoria")}
          meta={`d = ${fmtDecimal(d, 2)}`}
          defaultOpen
        >
          <LabeledSlider
            label={t("aprendizaje.decaimiento")}
            value={d}
            min={0}
            max={2}
            step={0.01}
            onChange={setD}
            hint={t("aprendizaje.decaimiento_hint")}
          />
        </CollapsibleSection>

        <CollapsibleSection
          title={t("aprendizaje.sec.variabilidad")}
          meta={condicion === "ninguno" ? "—" : `σ = ${sigma} min`}
          defaultOpen
        >
          <label className="flex flex-col gap-1">
            <span className="text-etiqueta text-muted">
              {t("aprendizaje.condicion")}
            </span>
            <select
              value={condicion}
              onChange={(e) =>
                setCondicion(e.target.value as ConfigPersona["condicion"])
              }
            >
              {CONDICIONES.map((c) => (
                <option key={c} value={c}>
                  {t(`aprendizaje.cond.${c}`)}
                </option>
              ))}
            </select>
          </label>
          <LabeledSlider
            label={t("aprendizaje.sigma")}
            value={sigma}
            min={0}
            max={120}
            step={5}
            unit="min"
            onChange={setSigma}
            disabled={condicion === "ninguno"}
          />
        </CollapsibleSection>

        {modo === "persona" && (
          <CollapsibleSection
            title={t("aprendizaje.sec.racha")}
            meta={kShocks > 0 ? `k = ${kShocks}` : "—"}
          >
            <LabeledSlider
              label={t("aprendizaje.k_shocks")}
              value={kShocks}
              min={0}
              max={20}
              step={1}
              onChange={setKShocks}
              hint={t("aprendizaje.k_shocks_hint")}
            />
            <LabeledSlider
              label={t("aprendizaje.delta")}
              value={delta}
              min={0}
              max={240}
              step={5}
              unit="min"
              onChange={setDelta}
              disabled={kShocks === 0}
            />
          </CollapsibleSection>
        )}

        {modo === "persona" && (
          <CollapsibleSection
            title={t("aprendizaje.sec.horizonte")}
            meta={`${dias} d · ${replicas}`}
          >
            <LabeledSlider
              label={t("aprendizaje.dias")}
              value={dias}
              min={30}
              max={500}
              step={10}
              onChange={setDias}
              hint={t("aprendizaje.dias_hint")}
            />
            <LabeledSlider
              label={t("aprendizaje.replicas")}
              value={replicas}
              min={50}
              max={2000}
              step={50}
              onChange={setReplicas}
            />
          </CollapsibleSection>
        )}

        <button
          type="button"
          className="run-btn"
          onClick={() => void (modo === "ciudad" ? correrCiudad() : correr())}
          disabled={!hayCorrida || estado === "running"}
        >
          {estado === "running"
            ? t("aprendizaje.corriendo")
            : `▶ ${t("aprendizaje.correr")}`}
        </button>
      </aside>

      <section className="main">
        <div className="hero">
          <div className="hero-head">
            <div>
              <h1 className="hero-title">{t("aprendizaje.title")}</h1>
              <p className="hero-sub" style={{ margin: "6px 0 0" }}>
                {t("aprendizaje.subtitle")}
              </p>
            </div>
            {estado === "running" ? (
              <EstadoPill estado="calculando">
                {t("hero.status_running")}
              </EstadoPill>
            ) : estado === "error" ? (
              <EstadoPill estado="error">{t("hero.status_error")}</EstadoPill>
            ) : res ? (
              <EstadoPill estado="ok">{t("aprendizaje.listo")}</EstadoPill>
            ) : null}
          </div>
        </div>

        {!hayCorrida && (
          <div className="stale-banner" role="status">
            <span>{t("aprendizaje.sin_corrida")}</span>
            <Link to="/sandbox">{t("aprendizaje.ir_a_transporte")}</Link>
          </div>
        )}

        {error && (
          <div className="stale-banner" role="alert">
            <span>{error}</span>
          </div>
        )}

        {modo === "ciudad" && esc && resCiudad && (
          <>
            <KPIStrip
              items={[
                {
                  label: t("aprendizaje.kpi.phi"),
                  value: fmtDecimal(resCiudad.phi.largo, 3),
                  sub: t("aprendizaje.ciudad.agentes", {
                    n: resCiudad.eligen.toLocaleString("es-CL"),
                  }),
                },
                {
                  label: t("aprendizaje.ciudad.dispersion"),
                  value: fmtDecimal(resCiudad.dispersion_iguales, 2),
                  sub: t("aprendizaje.ciudad.dispersion_sub"),
                },
                {
                  label: t("aprendizaje.ciudad.brecha"),
                  value: fmtDecimal(resCiudad.brecha_percepcion_min, 2),
                  unit: "min",
                  sub: t("aprendizaje.ciudad.brecha_sub"),
                },
                {
                  label: t("aprendizaje.ciudad.abandono"),
                  value: fmtDecimal(100 * resCiudad.abandono_metro, 1),
                  unit: "%",
                  sub: t("aprendizaje.ciudad.abandono_sub"),
                },
              ]}
            />

            <Panel
              n="01"
              title={t("aprendizaje.ciudad.quien_paga")}
              meta={t("aprendizaje.ciudad.quien_paga_meta")}
              cls="col-7"
            >
              <table className="tabla-datos">
                <thead>
                  <tr>
                    <th scope="col">{t("aprendizaje.ciudad.modo_mejor")}</th>
                    <th scope="col">{t("aprendizaje.ciudad.lleva_ruido")}</th>
                    <th scope="col">{t("aprendizaje.ciudad.personas")}</th>
                    <th scope="col">{t("aprendizaje.col.p_estrella")}</th>
                    <th scope="col">{t("aprendizaje.col.uniforme")}</th>
                    <th scope="col">{t("aprendizaje.col.phi")}</th>
                  </tr>
                </thead>
                <tbody>
                  {resCiudad.por_mejor.map((g) => (
                    <tr key={g.modo}>
                      <td>{g.modo}</td>
                      <td>
                        {g.lleva_ruido
                          ? t("aprendizaje.ciudad.si")
                          : t("aprendizaje.ciudad.no")}
                      </td>
                      <td>{g.n.toLocaleString("es-CL")}</td>
                      <td>{fmtDecimal(g.p_estrella, 3)}</td>
                      <td>{fmtDecimal(g.uniforme, 3)}</td>
                      <td>{fmtDecimal(g.phi.largo, 3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Panel>

            <Panel n="02" title={t("aprendizaje.ciudad.particion")} cls="col-5">
              <table className="tabla-datos">
                <thead>
                  <tr>
                    <th scope="col">{t("aprendizaje.ciudad.modo")}</th>
                    <th scope="col">{t("aprendizaje.ciudad.equilibrio")}</th>
                    <th scope="col">{t("aprendizaje.ciudad.final")}</th>
                    <th scope="col">Δ</th>
                  </tr>
                </thead>
                <tbody>
                  {resCiudad.modos.map((m, i) => (
                    <tr key={m}>
                      <td>{m}</td>
                      <td>
                        {fmtDecimal(100 * resCiudad.split_equilibrio[i]!, 2)}
                      </td>
                      <td>
                        {fmtDecimal(100 * resCiudad.split_ultimos[i]!, 2)}
                      </td>
                      <td>
                        {fmtDelta(
                          100 *
                            (resCiudad.split_ultimos[i]! -
                              resCiudad.split_equilibrio[i]!),
                          2,
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Panel>
          </>
        )}

        {modo === "persona" && caso && res && (
          <>
            <KPIStrip items={kpis} />

            {margenChico && (
              <div className="stale-banner" role="status">
                <span>
                  {t("aprendizaje.aviso_margen", {
                    margen: fmtDecimal(caso.margen_phi, 3),
                  })}
                </span>
              </div>
            )}

            <Panel
              n="01"
              title={t(
                vista === "promedio"
                  ? "aprendizaje.fig.titulo"
                  : "aprendizaje.fig.titulo_una",
              )}
              meta={
                vista === "promedio"
                  ? t("aprendizaje.fig.meta", {
                      dias: res.dias,
                      replicas: res.replicas,
                    })
                  : t("aprendizaje.fig.meta_una", {
                      dias: res.dias,
                      n: iReplica + 1,
                    })
              }
              cls="col-12"
            >
              {/* Si el núcleo que corre en el worker es anterior a `p_replicas`
                  —un wheel viejo en caché—, no hay réplicas que mostrar. Antes
                  esto tiraba la página entera con un error de render; ahora
                  simplemente no aparece el selector. */}
              {nReplicas > 0 && (
                <div className="fig-control">
                  <div
                    className="seg"
                    role="group"
                    aria-label={t("aprendizaje.fig.vista")}
                  >
                    {(["promedio", "replica"] as const).map((v) => (
                      <button
                        key={v}
                        type="button"
                        className={vista === v ? "active" : ""}
                        onClick={() => setVista(v)}
                      >
                        {t(`aprendizaje.fig.vista_${v}`)}
                      </button>
                    ))}
                  </div>
                  {vista === "replica" && (
                    <button
                      type="button"
                      className="fig-otra"
                      onClick={() => setIReplica((i) => (i + 1) % nReplicas)}
                    >
                      {t("aprendizaje.fig.otra")}
                    </button>
                  )}
                </div>
              )}
              <AprendizajeTrayectoria
                resultado={res}
                replica={
                  vista === "promedio" || nReplicas === 0
                    ? null
                    : iReplica % nReplicas
                }
              />
              <p className="fig-nota">
                {t(
                  vista === "promedio"
                    ? "aprendizaje.fig.nota"
                    : "aprendizaje.fig.nota_una",
                )}
              </p>
            </Panel>

            <Panel n="02" title={t("aprendizaje.tabla.titulo")} cls="col-6">
              <table className="tabla-datos">
                <thead>
                  <tr>
                    <th scope="col">{t("aprendizaje.tabla.ventana")}</th>
                    <th scope="col">{t("aprendizaje.tabla.dias")}</th>
                    <th scope="col">{t("aprendizaje.col.s")}</th>
                    <th scope="col">{t("aprendizaje.col.phi")}</th>
                    <th scope="col">{t("aprendizaje.tabla.invertidos")}</th>
                  </tr>
                </thead>
                <tbody>
                  {(["corto", "medio", "largo"] as const).map((w) => {
                    const v = res.ventanas[w];
                    return (
                      <tr key={w}>
                        <td>{t(`aprendizaje.ventana.${w}`)}</td>
                        <td>{`${v.desde}–${v.hasta}`}</td>
                        <td>{fmtDecimal(v.s, 3)}</td>
                        <td>{fmtDecimal(v.phi, 2)}</td>
                        <td>{fmtDecimal(100 * v.invertidos, 1)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </Panel>

            {res.shock && (
              <Panel n="03" title={t("aprendizaje.shock.titulo")} cls="col-6">
                <table className="tabla-datos">
                  <tbody>
                    <tr>
                      <td>{t("aprendizaje.shock.w_k")}</td>
                      <td>{fmtDecimal(res.shock.w_k, 4)}</td>
                    </tr>
                    <tr>
                      <td>{t("aprendizaje.shock.critico")}</td>
                      <td>
                        {`${fmtDecimal(res.shock.delta_critico_min, 1)} min`}
                      </td>
                    </tr>
                    <tr>
                      <td>{t("aprendizaje.shock.analitica")}</td>
                      <td>{fmtDecimal(res.shock.p_post_analitica, 4)}</td>
                    </tr>
                    <tr>
                      <td>{t("aprendizaje.shock.simulada")}</td>
                      <td>
                        {res.shock.p_post_simulada == null
                          ? "—"
                          : fmtDecimal(res.shock.p_post_simulada, 4)}
                      </td>
                    </tr>
                    <tr>
                      <td>{t("aprendizaje.shock.llegan")}</td>
                      <td>
                        {`${fmtDecimal(100 * res.shock.llegan_a_k, 1)} %`}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </Panel>
            )}
          </>
        )}

        <Panel
          n="A"
          title={t("aprendizaje.teoria.titulo")}
          meta={t("aprendizaje.teoria.meta")}
          cls="col-12"
        >
          <TeoriaAprendizaje modo={modo} />
        </Panel>
      </section>
    </div>
  );
}
