import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Tooltip,
  Legend,
  Filler,
  RadarController,
  RadialLinearScale,
  BubbleController,
  ScatterController,
  LogarithmicScale,
} from 'chart.js';
import { SankeyController, Flow } from 'chartjs-chart-sankey';
import { BoxPlotController, BoxAndWiskers, ViolinController, Violin } from '@sgratzl/chartjs-chart-boxplot';
import { TreemapController, TreemapElement } from 'chartjs-chart-treemap';
import { MatrixController, MatrixElement } from 'chartjs-chart-matrix';
import zoomPlugin from 'chartjs-plugin-zoom';
import annotationPlugin from 'chartjs-plugin-annotation';

// NOTE: ChartDataLabels is NOT registered globally — it's passed per-chart
// via the plugins prop to avoid showing labels on every chart.

ChartJS.register(
  // Core scales & elements
  CategoryScale,
  LinearScale,
  LogarithmicScale,
  RadialLinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Tooltip,
  Legend,
  Filler,

  // Core controllers for Scatter, Bubble, Radar
  RadarController,
  BubbleController,
  ScatterController,

  // Sankey
  SankeyController,
  Flow,

  // Box plot & Violin
  BoxPlotController,
  BoxAndWiskers,
  ViolinController,
  Violin,

  // Treemap
  TreemapController,
  TreemapElement,

  // Matrix / Heatmap
  MatrixController,
  MatrixElement,

  // Plugins
  zoomPlugin,
  annotationPlugin,
);
