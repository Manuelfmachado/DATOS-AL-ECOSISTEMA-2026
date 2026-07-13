import type { SVGProps } from "react";
import {
  ChartBar,
  ChartLine,
  ChartPie,
  ChartTrend,
  ChartBarTrendUp,
  ChartSuccess2,
  Briefcase,
  Buildings,
  Bookmark,
  Bulb,
  DollarCircle,
  Rocket,
  Microphone,
  ChatRoundDots,
  DocumentText2,
  Map,
  Bag,
  Bank,
  Teacher2,
  DocumentNormal2,
  Truck,
  Login2,
  Logout2,
  Home,
  Eye,
  ArrowRight,
  ArrowLeft,
  ArrowUp,
  ArrowDown,
  Check,
  CloseCircle2,
  InfoCircle,
  Search,
  Filter,
  Download,
  Upload,
  Copy,
  Phone,
  CallSlash2,
  Courthouse2,
  Code,
  Cpu,
  Database,
  Calendar,
  Clock,
  BulbBolt,
  ChartFail2,
  Building3,
  CalendarEdit2,
} from "reicon-react";

export type IconWeight = "Outline" | "Filled";
export type IconSize = number | string;

export interface IconProps extends Omit<SVGProps<SVGSVGElement>, "size" | "color"> {
  size?: IconSize;
  weight?: IconWeight;
  color?: string;
}

const base = (weight: IconWeight, size: IconSize, color: string): SVGProps<SVGSVGElement> => ({
  width: size,
  height: size,
  color,
});

export const Icon = {
  Observatorio: (p: IconProps = {}) => <ChartBar {...base(p.weight ?? "Outline", p.size ?? 20, p.color ?? "#d4af37")} {...p} />,
  ObservatorioLinea: (p: IconProps = {}) => <ChartLine {...base(p.weight ?? "Outline", p.size ?? 20, p.color ?? "#d4af37")} {...p} />,
  ObservatorioTorta: (p: IconProps = {}) => <ChartPie {...base(p.weight ?? "Outline", p.size ?? 20, p.color ?? "#d4af37")} {...p} />,
  ObservatorioMapa: (p: IconProps = {}) => <Map {...base(p.weight ?? "Outline", p.size ?? 20, p.color ?? "#d4af37")} {...p} />,

  Prediccion: (p: IconProps = {}) => <ChartTrend {...base(p.weight ?? "Outline", p.size ?? 20, p.color ?? "#d4af37")} {...p} />,
  PrediccionUp: (p: IconProps = {}) => <ChartBarTrendUp {...base(p.weight ?? "Outline", p.size ?? 20, p.color ?? "#d4af37")} {...p} />,
  PrediccionExito: (p: IconProps = {}) => <ChartSuccess2 {...base(p.weight ?? "Outline", p.size ?? 20, p.color ?? "#d4af37")} {...p} />,

  Match: (p: IconProps = {}) => <Briefcase {...base(p.weight ?? "Outline", p.size ?? 20, p.color ?? "#d4af37")} {...p} />,
  MatchEmpresa: (p: IconProps = {}) => <Buildings {...base(p.weight ?? "Outline", p.size ?? 20, p.color ?? "#d4af37")} {...p} />,
  MatchUniversidad: (p: IconProps = {}) => <Building3 {...base(p.weight ?? "Outline", p.size ?? 20, p.color ?? "#d4af37")} {...p} />,
  MatchGuardado: (p: IconProps = {}) => <Bookmark {...base(p.weight ?? "Outline", p.size ?? 20, p.color ?? "#d4af37")} {...p} />,

  Emprende: (p: IconProps = {}) => <Bulb {...base(p.weight ?? "Outline", p.size ?? 20, p.color ?? "#d4af37")} {...p} />,
  EmprendeIdea: (p: IconProps = {}) => <BulbBolt {...base(p.weight ?? "Outline", p.size ?? 20, p.color ?? "#d4af37")} {...p} />,
  EmprendeDinero: (p: IconProps = {}) => <DollarCircle {...base(p.weight ?? "Outline", p.size ?? 20, p.color ?? "#d4af37")} {...p} />,
  EmprendeLanzar: (p: IconProps = {}) => <Rocket {...base(p.weight ?? "Outline", p.size ?? 20, p.color ?? "#d4af37")} {...p} />,

  Coach: (p: IconProps = {}) => <Microphone {...base(p.weight ?? "Outline", p.size ?? 20, p.color ?? "#d4af37")} {...p} />,
  CoachChat: (p: IconProps = {}) => <ChatRoundDots {...base(p.weight ?? "Outline", p.size ?? 20, p.color ?? "#d4af37")} {...p} />,
  CoachDocumento: (p: IconProps = {}) => <DocumentText2 {...base(p.weight ?? "Outline", p.size ?? 20, p.color ?? "#d4af37")} {...p} />,

  Simulacion: (p: IconProps = {}) => <CalendarEdit2 {...base(p.weight ?? "Outline", p.size ?? 20, p.color ?? "#d4af37")} {...p} />,

  Sidebar: {
    Observatorio: (p: IconProps = {}) => <ChartBar {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Prediccion: (p: IconProps = {}) => <ChartTrend {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Match: (p: IconProps = {}) => <Briefcase {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Emprende: (p: IconProps = {}) => <Bulb {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Coach: (p: IconProps = {}) => <Microphone {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Simulacion: (p: IconProps = {}) => <CalendarEdit2 {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
  },

  Accion: {
    Buscar: (p: IconProps = {}) => <Search {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Filtro: (p: IconProps = {}) => <Filter {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Descargar: (p: IconProps = {}) => <Download {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Subir: (p: IconProps = {}) => <Upload {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Copiar: (p: IconProps = {}) => <Copy {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Derecha: (p: IconProps = {}) => <ArrowRight {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Izquierda: (p: IconProps = {}) => <ArrowLeft {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Arriba: (p: IconProps = {}) => <ArrowUp {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Abajo: (p: IconProps = {}) => <ArrowDown {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Check: (p: IconProps = {}) => <Check {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Cerrar: (p: IconProps = {}) => <CloseCircle2 {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Info: (p: IconProps = {}) => <InfoCircle {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Ojo: (p: IconProps = {}) => <Eye {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Inicio: (p: IconProps = {}) => <Home {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Login: (p: IconProps = {}) => <Login2 {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Logout: (p: IconProps = {}) => <Logout2 {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Telefono: (p: IconProps = {}) => <Phone {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    TelefonoOff: (p: IconProps = {}) => <CallSlash2 {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Calendario: (p: IconProps = {}) => <Calendar {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Reloj: (p: IconProps = {}) => <Clock {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
  },

  Kpi: {
    Trabajo: (p: IconProps = {}) => <Briefcase {...base(p.weight ?? "Outline", p.size ?? 28, p.color ?? "#d4af37")} {...p} />,
    Desempleo: (p: IconProps = {}) => <ChartFail2 {...base(p.weight ?? "Outline", p.size ?? 28, p.color ?? "#d4af37")} {...p} />,
    Mapa: (p: IconProps = {}) => <Map {...base(p.weight ?? "Outline", p.size ?? 28, p.color ?? "#d4af37")} {...p} />,
    Documento: (p: IconProps = {}) => <DocumentText2 {...base(p.weight ?? "Outline", p.size ?? 28, p.color ?? "#d4af37")} {...p} />,
  },

  Profesion: {
    Admin: (p: IconProps = {}) => <Building3 {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Ingenieria: (p: IconProps = {}) => <Cpu {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Datos: (p: IconProps = {}) => <Database {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Programador: (p: IconProps = {}) => <Code {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Salud: (p: IconProps = {}) => <DocumentNormal2 {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Educacion: (p: IconProps = {}) => <Teacher2 {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Derecho: (p: IconProps = {}) => <Courthouse2 {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Finanzas: (p: IconProps = {}) => <Bank {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Comercio: (p: IconProps = {}) => <Bag {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
    Logistica: (p: IconProps = {}) => <Truck {...base(p.weight ?? "Outline", p.size ?? 18, p.color ?? "#d4af37")} {...p} />,
  },
};

export default Icon;
