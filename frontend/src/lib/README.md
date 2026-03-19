# lib

Shared frontend utilities used across dashboard features.

## Files

### `chartSetup.js`
Registers all Chart.js primitives/plugins used in the app, including Sankey support.

- Side effect only: import once at app startup before rendering chart components.

```js
import './lib/chartSetup';
```

Registered pieces:
- Chart.js scales/elements: `CategoryScale`, `LinearScale`, `PointElement`, `LineElement`, `BarElement`, `ArcElement`
- Plugins: `Tooltip`, `Legend`, `Filler`
- Sankey plugin: `SankeyController`, `Flow`

### `constants.js`
Exports common shared constants.

- `API_BASE`: default API prefix (`/api`)
- `customStyles`: CSS string for theme variables and utility animations/classes

```js
import { API_BASE, customStyles } from './lib/constants';
```

`customStyles` contains:
- Theme tokens (`--frammer-*` CSS variables)
- `flowRight` animation and `.dot-flow` helpers
- `tickerFlow` animation and `.animate-ticker`
- `.hide-scrollbar` helper

### `formatters.js`
Value formatting helpers for UI rendering.

- `formatNumber(value)`: locale-separated number (or `-` for invalid input)
- `formatPct(value)`: percentage with 2 decimals (or `-`)
- `formatHours(value)`: seconds to hours with 1 decimal, suffixed with `hrs` (or `-`)

```js
import { formatNumber, formatPct, formatHours } from './lib/formatters';
```

## Conventions
- Keep this folder focused on stateless, reusable helpers.
- Prefer named exports.
- Guard formatters against `null`, `undefined`, and non-numeric values.
- If a helper has side effects (like chart registration), document import timing clearly.
