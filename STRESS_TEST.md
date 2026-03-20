# Agent Stress Test — Comprehensive Question Battery

> **How to use**: Copy-paste each question into the chat input. After each response, verify the expected behavior. Multi-turn tests must be run sequentially within the same conversation. Start a new conversation for each section unless noted.

---

## Section 1: Conversational Handling (No Data Queries)

The agent should respond directly without calling any tools.

| # | Question | Expected |
|---|----------|----------|
| 1.1 | `Hello` | Friendly greeting, no SQL, no chart |
| 1.2 | `What can you do?` | Describes capabilities (SQL, charts, tables, AI insights) |
| 1.3 | `Thanks for the help!` | Brief acknowledgment, no tools fired |
| 1.4 | `Who built you?` | Says Frammer AI / analytics assistant, no data query |
| 1.5 | `Tell me a joke about data` | Responds conversationally, no SQL |

---

## Section 2: Discovery & Schema Questions

The agent should use schema/metric tools but no SQL execution.

| # | Question | Expected |
|---|----------|----------|
| 2.1 | `What tables are available in the database?` | Lists: raw_videos, created_assets, published_posts, post_distribution, raw_video_channel, channels, users, clients |
| 2.2 | `What columns does the raw_videos table have?` | Lists: Video_ID, User_ID, Headline, Source_URL, Upload_Date, Input_Type, Language, Uploaded_Duration |
| 2.3 | `What languages exist in the data?` | Should return "hi" and "en" (from schema profile or column values) |
| 2.4 | `What are the different output types for assets?` | Full package, Chapters, Summary, Key moments, My Key moments |
| 2.5 | `What platforms are available for publishing?` | Facebook, Instagram, Linkedin, Reels, Shorts, X, Youtube, Threads |
| 2.6 | `How are the tables related?` | Explains: raw_videos → created_assets → published_posts → post_distribution + channel/user ownership |
| 2.7 | `What input types exist?` | interview, speech, news bulletin, discussion-show, special reports, debate, press conference |
| 2.8 | `How many clients are there?` | 4 (Client 1-4) |
| 2.9 | `What channels does Client 1 have?` | Single-letter channels A through R |
| 2.10 | `What metrics can you calculate?` | Lists: uploads, assets, conversions, creation rate, publish rate, durations, trends, etc. |

---

## Section 3: Simple Single-Metric Queries

One query, one number, typically no chart needed.

| # | Question | Expected |
|---|----------|----------|
| 3.1 | `How many videos have been uploaded?` | Single number ~10,700. KPI card or text. No chart. |
| 3.2 | `How many assets have been created?` | ~53,700. Single KPI. |
| 3.3 | `How many posts have been published?` | Should use COUNT(DISTINCT Asset_ID) not Post_ID. Verify number. |
| 3.4 | `What is the total uploaded duration in hours?` | SUM(Uploaded_Duration)/3600. Single number. |
| 3.5 | `What is the average uploaded duration per video?` | AVG(Uploaded_Duration). Single number in seconds. |
| 3.6 | `How many distinct users have uploaded videos?` | COUNT(DISTINCT User_ID) from raw_videos. |
| 3.7 | `How many channels are there?` | COUNT from channels table. ~60. |
| 3.8 | `What percentage of assets get published?` | Conversion rate formula. Single percentage. |
| 3.9 | `How many videos were uploaded in English?` | WHERE Language = 'en'. Uses exact value from schema. |
| 3.10 | `What is the total published duration?` | SUM(Published_Duration) from published_posts. |

---

## Section 4: Comparison Queries (Bar Charts)

Should produce bar chart artifacts.

| # | Question | Expected |
|---|----------|----------|
| 4.1 | `Show uploads by language` | Bar chart: hi vs en. 2 bars. |
| 4.2 | `Compare upload volume across input types` | Bar chart: 7 bars (interview, speech, etc.) |
| 4.3 | `Which channels have the most uploads?` | Bar or horizontal-bar: channels ranked by upload count |
| 4.4 | `Show asset count by output type` | Bar chart: 5 output types |
| 4.5 | `Compare published posts across platforms` | Bar chart: 8 platforms |
| 4.6 | `Top 5 users by upload count` | horizontal-bar (rankings with names) |
| 4.7 | `Compare Client 1 vs Client 2 total uploads` | Bar chart: 2 bars |
| 4.8 | `Show average uploaded duration by language` | Bar: 2 bars (hi, en) with AVG duration |
| 4.9 | `Which input type has the longest average duration?` | Bar or horizontal-bar, sorted |
| 4.10 | `Compare creation rate across channels A, B, and C` | Bar: 3 bars with creation_rate formula |

---

## Section 5: Stacked Bar / Multi-Metric Composition

Should trigger stacked-bar chart type.

| # | Question | Expected |
|---|----------|----------|
| 5.1 | `Show uploads by channel, broken down by language` | stacked-bar: channels on X, stacked by hi/en |
| 5.2 | `Compare channels across total uploads, assets created, and published posts` | stacked-bar: 3 metrics stacked per channel |
| 5.3 | `Show asset volume by output type for each client` | stacked-bar or grouped bar |
| 5.4 | `Break down published posts by platform for the top 5 channels` | stacked-bar: 5 channels, stacked by platform |

---

## Section 6: Trend / Time-Series Queries (Line Charts)

Should produce line or area charts with date on X-axis.

| # | Question | Expected |
|---|----------|----------|
| 6.1 | `Show the monthly upload trend` | Line chart: months on X, upload count on Y |
| 6.2 | `Show weekly upload volume over time` | Line chart with weekly granularity. Uses date_trunc('week', ...) |
| 6.3 | `Show the monthly trend of assets created vs published` | Line chart: 2 lines (created count, published count) |
| 6.4 | `How has the upload volume changed month over month?` | Line with trend. May include WoW/MoM calculation. |
| 6.5 | `Show the monthly upload trend by language` | area chart (stacked line): 2 filled series (hi, en) by month |
| 6.6 | `Show the rolling 7-day average of uploads` | Line chart using window function |
| 6.7 | `What's the publication trend over the last 6 months?` | Line chart, filtered by date range. Agent should call get_time first. |
| 6.8 | `Show monthly created asset duration trend` | Line chart: SUM(Created_Duration) by month |

---

## Section 7: Proportion Queries (Pie / Doughnut)

Should produce pie or doughnut charts.

| # | Question | Expected |
|---|----------|----------|
| 7.1 | `What share of uploads are in each language?` | Pie or doughnut: hi vs en (2 slices) |
| 7.2 | `Show the proportion of assets by output type` | Doughnut: 5 slices |
| 7.3 | `What percentage of published posts go to each platform?` | Doughnut: 8 slices (may prefer pie if ≤6) |
| 7.4 | `Show the share of uploads by client` | Pie: 4 slices |
| 7.5 | `What fraction of uploaded videos are interviews vs speeches?` | Pie: 2+ slices from Input_Type |

---

## Section 8: Conversion & Funnel Queries (Critical Business Logic)

These test the hardest SQL patterns. Verify conversion_rate uses Asset_ID not Post_ID, and groups through rv/rvc not post_distribution.

| # | Question | Expected |
|---|----------|----------|
| 8.1 | `What is the overall conversion rate from assets to published?` | Single percentage. Formula: COUNT(DISTINCT pp.Asset_ID) / COUNT(DISTINCT ca.Asset_ID) * 100 |
| 8.2 | `Show conversion rate by channel` | Bar chart. Must join through rv → rvc for Channel_Name, NOT post_distribution |
| 8.3 | `Which channel has the highest conversion rate?` | Single answer with channel name and rate |
| 8.4 | `Show the full funnel: uploads → assets → published for each channel` | Stacked bar or multi-metric comparison |
| 8.5 | `What is the creation rate per video by language?` | creation_rate formula grouped by Language |
| 8.6 | `Compare conversion rates across clients` | Must join users for Client_Name grouping |
| 8.7 | `Which output type has the best publication rate?` | Conversion by Output_Type |
| 8.8 | `Show the funnel drop-off at each stage` | Uploads → Assets created → Published. Show absolute + rate. |
| 8.9 | `What percentage of English videos get published vs Hindi?` | Conversion grouped by Language |
| 8.10 | `Show conversion rate by channel for Client 1 only` | Filtered + conversion. Tests both auth scope and formula. |

---

## Section 9: Filtering & Scoping

Tests exact value matching and filter combinations.

| # | Question | Expected |
|---|----------|----------|
| 9.1 | `Show uploads for Client 1 only` | WHERE u.Client_Name = 'Client 1'. Uses exact casing. |
| 9.2 | `How many Hindi interviews were uploaded?` | WHERE Language = 'hi' AND LOWER(Input_Type) = 'interview' |
| 9.3 | `Show assets created from speech videos` | WHERE LOWER(Input_Type) = 'speech' |
| 9.4 | `How many posts were published on YouTube?` | WHERE Published_Platform = 'Youtube' (exact casing!) |
| 9.5 | `Show uploads by channel A` | WHERE Channel_Name = 'A'. Exact single-letter match. |
| 9.6 | `Compare channels A, B, and C across all metrics` | Multiple queries, filtered by Channel_Name IN ('A','B','C') |
| 9.7 | `Show all Full package assets` | WHERE Output_Type = 'Full package' |
| 9.8 | `How many videos were uploaded after January 2024?` | Date filtering with to_date(). Should call get_time if "recently" is mentioned. |
| 9.9 | `Show published posts on Instagram and Facebook combined` | WHERE Published_Platform IN ('Instagram', 'Facebook') |
| 9.10 | `Show upload trend for debate videos only` | Filter Input_Type + time series |

---

## Section 10: Advanced Analytics

Tests complex SQL patterns: CTEs, window functions, subqueries.

| # | Question | Expected |
|---|----------|----------|
| 10.1 | `What is the week-over-week growth in uploads?` | CTE with LAG() or self-join. Shows WoW % change. |
| 10.2 | `Show the rolling 30-day average of published posts` | Window function: AVG() OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) |
| 10.3 | `Which users have uploaded videos in more than 3 different languages?` | GROUP BY User_ID HAVING COUNT(DISTINCT Language) > 3. Trick: only 2 languages exist, so result should be empty. |
| 10.4 | `Show the top 3 channels by upload-to-publish conversion rate` | Conversion formula + ORDER BY + LIMIT 3 |
| 10.5 | `For each channel, show the most popular output type` | Requires window function or correlated subquery (RANK/ROW_NUMBER) |
| 10.6 | `What's the average time between upload and asset creation?` | Date diff between Upload_Date and Create_Date. May need date casting. |
| 10.7 | `Show the cumulative upload count over time` | SUM() OVER (ORDER BY month) running total |
| 10.8 | `Which channels have zero published posts?` | LEFT JOIN + WHERE pp.Asset_ID IS NULL |
| 10.9 | `Show the Pareto distribution of uploads by user (top 20% of users)` | Complex: percentile_cont + cumulative percentage |
| 10.10 | `Compare this month's uploads to last month's` | Requires get_time step + date math |

---

## Section 11: Distribution Charts (Box / Violin)

Tests box plot SQL patterns with percentile functions.

| # | Question | Expected |
|---|----------|----------|
| 11.1 | `Show the distribution of uploaded duration by language` | Box plot with SQL using PERCENTILE_CONT(0.25/0.5/0.75) WITHIN GROUP |
| 11.2 | `Show the distribution of created asset duration by output type` | Box plot: 5 categories |
| 11.3 | `Compare the duration distribution of published vs unpublished assets` | Violin or box: 2 categories |
| 11.4 | `Show the duration spread for each input type` | Box: 7 categories with min/Q1/median/Q3/max |

---

## Section 12: Correlation Charts (Scatter / Bubble)

Tests scatter and bubble chart data shapes.

| # | Question | Expected |
|---|----------|----------|
| 12.1 | `Is there a correlation between upload duration and number of assets created per video?` | Scatter: X=duration, Y=asset count per video |
| 12.2 | `Plot upload count vs conversion rate by channel` | Scatter: each point = channel, X=uploads, Y=conversion% |
| 12.3 | `Show the relationship between video count and average duration by user` | Scatter with many points |
| 12.4 | `Create a bubble chart of channels: uploads vs published count vs asset count` | Bubble: X=uploads, Y=published, size=assets |

---

## Section 13: Radar Charts (Multi-Dimensional Profile)

Tests radar chart data transposition.

| # | Question | Expected |
|---|----------|----------|
| 13.1 | `Compare channels A, B, and C across uploads, assets, conversion rate, and average duration` | Radar: 4 metrics, 3 entities (channels) |
| 13.2 | `Profile the top 3 clients across all KPIs` | Radar: multiple metrics per client |
| 13.3 | `Spider chart comparing English vs Hindi across uploads, assets, published, and duration` | Radar: 2 datasets (languages), 4+ metrics |

---

## Section 14: Heatmap Charts

Tests cross-tabulation with 2 dimensions + value.

| # | Question | Expected |
|---|----------|----------|
| 14.1 | `Show a heatmap of upload count by channel and language` | Heatmap: X=channel, Y=language, color=count |
| 14.2 | `Create a heatmap of asset count by output type and channel for Client 1` | Heatmap: filtered + 2D cross-tab |
| 14.3 | `Show the cross-tabulation of input type vs language for uploads` | Heatmap: 7 input types × 2 languages |
| 14.4 | `Heatmap of published posts by platform and channel` | Heatmap: 8 platforms × N channels |

---

## Section 15: Treemap Charts

Tests hierarchical data shapes.

| # | Question | Expected |
|---|----------|----------|
| 15.1 | `Show a treemap of uploads by client and channel` | Treemap: nested by client > channel, sized by upload count |
| 15.2 | `Treemap of asset count by output type` | Treemap: 5 rectangles sized by count |
| 15.3 | `Show the proportion of published posts by platform as a treemap` | Treemap: 8 rectangles |

---

## Section 16: Horizontal Bar (Rankings)

| # | Question | Expected |
|---|----------|----------|
| 16.1 | `Rank all channels by total upload count` | horizontal-bar: sorted descending |
| 16.2 | `Top 10 users by number of published assets` | horizontal-bar: 10 bars, names on Y axis |
| 16.3 | `Rank input types by average duration` | horizontal-bar: 7 bars |

---

## Section 17: Polar Area / Doughnut

| # | Question | Expected |
|---|----------|----------|
| 17.1 | `Show upload share by client as a doughnut chart` | Doughnut: 4 slices with percentage labels |
| 17.2 | `Polar area chart of platform usage` | Polar area: 8 segments |

---

## Section 18: Area Charts (Stacked Time Series)

| # | Question | Expected |
|---|----------|----------|
| 18.1 | `Show the monthly upload trend broken down by input type as a stacked area` | Area chart: 7 filled series stacked by month |
| 18.2 | `Show monthly asset creation by output type` | Area: 5 stacked series over time |

---

## Section 19: Multi-Turn Conversations (Drill-Down)

Run these sequentially in ONE conversation. Tests working memory and context.

### Conversation A: Progressive Drill-Down
| Turn | Question | Expected |
|------|----------|----------|
| A1 | `Show me the overall pipeline health` | Overview: uploads → assets → published. Multiple charts/metrics. |
| A2 | `Which channels are underperforming?` | Should use context from A1 to focus on low-conversion channels |
| A3 | `Drill into channel D specifically` | Detailed metrics for channel D only |
| A4 | `What output types are failing for that channel?` | Should remember "channel D" from A3 |
| A5 | `Compare it to channel A` | Should compare D vs A |
| A6 | `Show me the trend for both over the last year` | Time series for both channels |

### Conversation B: Refinement
| Turn | Question | Expected |
|------|----------|----------|
| B1 | `How many uploads per month?` | Monthly trend line |
| B2 | `Break that down by language` | Stacked area by language per month |
| B3 | `Only show the last 6 months` | Should filter by date. Needs get_time. |
| B4 | `What about just English?` | Further filter to Language = 'en' |
| B5 | `Now show it as a bar chart instead` | Same data, different viz |

### Conversation C: Follow-Up Questions
| Turn | Question | Expected |
|------|----------|----------|
| C1 | `What's the conversion rate?` | Single number |
| C2 | `Why is it so low?` | Should investigate: which stages lose the most, which channels/types underperform |
| C3 | `Which output type converts the best?` | Conversion by Output_Type |
| C4 | `And the worst?` | Should reference C3 results, highlight the worst |

### Conversation D: Topic Switch
| Turn | Question | Expected |
|------|----------|----------|
| D1 | `Show uploads by language` | Bar chart |
| D2 | `Now show me something completely different - what platforms get the most posts?` | Clean topic switch, should not confuse with language data |
| D3 | `Go back to the language analysis and add duration` | Should recall D1 context |

---

## Section 20: Edge Cases & Error Handling

| # | Question | Expected |
|---|----------|----------|
| 20.1 | `Show me data from the app_users table` | Should REFUSE or return error (app_users is in forbidden list) |
| 20.2 | `Delete all videos` | Should NOT execute. Agent should recognize this as non-analytical. |
| 20.3 | `` (empty message) | Frontend should block this before sending |
| 20.4 | `Show uploads for a channel called ZZZZZ` | Should return empty results gracefully ("no data found") |
| 20.5 | `What is the upload count divided by zero?` | SQL should use NULLIF to prevent division by zero |
| 20.6 | `Show me the trend for the year 3000` | Empty results (no data in future). Agent should note no data. |
| 20.7 | `SELECT * FROM raw_videos` | Agent should plan a proper query, not pass raw SQL through |
| 20.8 | `Show me everything` | Extremely vague. Agent should ask for clarification or give overview. |
| 20.9 | `Compare all 60 channels on 10 different metrics simultaneously` | Agent should handle gracefully — maybe limit to top N or split into multiple queries |
| 20.10 | `sdkfjhsdkfjh` | Gibberish. Agent should ask for clarification. |
| 20.11 | `Show uploads for "Client 2"` | Tests exact value matching — should use Client_Name = 'Client 2' |
| 20.12 | `How many videos were uploaded yesterday?` | Should call get_time first, then compute yesterday's date |
| 20.13 | `Show data for client 2` | Tests case insensitivity — user says "client 2", DB has "Client 2". Agent should use get_column_values or schema sample values to get exact casing. |

---

## Section 21: Parallel Execution Stress

These queries require MULTIPLE independent SQL queries that should run in parallel.

| # | Question | Expected |
|---|----------|----------|
| 21.1 | `Give me a complete dashboard: total uploads, total assets, total published, conversion rate, and the monthly trend` | Should plan 2+ parallel SQL steps (aggregates + time series) + charts. Check logs for concurrent execution. |
| 21.2 | `Compare all 4 clients across uploads, assets, published, conversion rate, and creation rate` | Multiple metrics, should plan parallel queries for each metric |
| 21.3 | `Show me: (1) uploads by language, (2) assets by output type, (3) published by platform` | 3 independent queries + 3 charts. Should all run in parallel. |
| 21.4 | `Analyze the full pipeline: show funnel stages, conversion by channel, trend over time, and platform distribution` | 4+ parallel queries |

---

## Section 22: Chart Interactivity Verification

After getting any chart, verify these interactive features in the workbench:

| # | Action | Expected |
|---|--------|----------|
| 22.1 | Hover over any bar/line/point | Dark tooltip with formatted number, rounded corners, styled fonts |
| 22.2 | Scroll wheel on a bar/line chart | Chart zooms in on X-axis |
| 22.3 | Click "Reset Zoom" button | Chart returns to original view |
| 22.4 | Click a legend item | That series toggles off/on |
| 22.5 | Switch chart type via dropdown | Chart re-renders correctly with new type |
| 22.6 | Check pie/doughnut chart | Should show percentage labels on slices |
| 22.7 | Open Data tab | Paginated table, sortable columns, CSV export |
| 22.8 | Open Query tab | SQL with syntax highlighting (blue keywords, amber strings, green numbers) |
| 22.9 | Multiple charts in workbench | Tab selector above chart to switch between them |
| 22.10 | Chart Summary Strip | Shows "N data points · Max: X · Min: Y · Avg: Z" below chart |

---

## Section 23: Streaming / Progressive UI Verification

| # | Action | Expected |
|---|--------|----------|
| 23.1 | Send any data query | See "Analyzing question..." phase first |
| 23.2 | Watch plan appear | "Execution Plan" box with step list (circles for pending) |
| 23.3 | Watch steps complete | Green checkmarks appear one by one as steps finish |
| 23.4 | Failed step | Red triangle icon for failed steps |
| 23.5 | Phase transitions | Planning → Executing → (Repairing if errors) → Synthesizing |
| 23.6 | Final message | Chat bubble replaces streaming indicator with full response |
| 23.7 | Canvas auto-open | If charts generated, right panel should auto-open |

---

## Section 24: Repair Mechanism

Intentionally trigger SQL errors to test the repair loop.

| # | Question | Expected |
|---|----------|----------|
| 24.1 | `Show uploads grouped by month using the column "upload_date"` | Agent may generate wrong column name (lowercase). Repair should fix to "Upload_Date". |
| 24.2 | `Show the average duration for each video category` | No "category" column exists. Agent should adapt or repair to use Input_Type or Output_Type. |
| 24.3 | `Join raw_videos directly with published_posts` | Missing bridge table (created_assets). If agent makes this mistake, repair should fix the join chain. |

---

## Section 25: Memory & Context Persistence

| # | Question | Expected |
|---|----------|----------|
| 25.1 | Send a query, then refresh the browser. Click the conversation in sidebar. | Messages should reload from persistence. |
| 25.2 | In a long conversation (5+ turns), ask `What have we discussed so far?` | Agent should reference working memory summary. |
| 25.3 | Start new conversation, ask same question as old one | Should not carry over context from old conversation. |
| 25.4 | Delete a conversation from sidebar | Conversation should disappear. Clicking it should not work. |

---

## Section 26: Relative Time Queries

These should trigger `get_time` step before SQL.

| # | Question | Expected |
|---|----------|----------|
| 26.1 | `How many videos were uploaded today?` | get_time → compute today → filter Upload_Date |
| 26.2 | `Show uploads from last week` | get_time → date range for last 7 days |
| 26.3 | `What was the upload volume last month?` | get_time → previous calendar month |
| 26.4 | `Compare this month to the previous month` | get_time → 2 date ranges |
| 26.5 | `Show the trend for the last 3 months` | get_time → filter last 90 days |

---

## Section 27: Multi-Chart Generation

These should produce MULTIPLE charts in a single response.

| # | Question | Expected |
|---|----------|----------|
| 27.1 | `Show me a bar chart of uploads by language AND a pie chart of platform distribution` | 2 separate chart artifacts. Workbench should have tab selector. |
| 27.2 | `Give me 3 charts: upload trend, conversion by channel, and platform breakdown` | 3 charts, 3 SQL queries (should run in parallel), tab selector in workbench |
| 27.3 | `Full analysis of channel A: show upload trend, asset breakdown by type, and conversion rate comparison` | Multiple queries + charts for one channel |

---

## Section 28: Data Volume & Limits

| # | Question | Expected |
|---|----------|----------|
| 28.1 | `Show me all raw videos` | Should use aggregation (GROUP BY) since >100 rows. Should NOT return 10,000+ raw rows. |
| 28.2 | `List every single asset` | Same — should aggregate, not dump 53k rows |
| 28.3 | `Show all users with their upload counts` | Should aggregate per user, not raw join |

---

## Section 29: Complex Natural Language

Tests the planner's ability to interpret ambiguous or complex questions.

| # | Question | Expected |
|---|----------|----------|
| 29.1 | `Which channels are losing conversion?` | Identify channels with below-average conversion rates |
| 29.2 | `What should I investigate next?` | Open-ended. Agent should suggest areas of interest based on data patterns. |
| 29.3 | `Are we getting better or worse?` | Trend analysis — compare recent period to earlier period |
| 29.4 | `Where is the bottleneck in our pipeline?` | Funnel analysis — identify the stage with the biggest drop-off |
| 29.5 | `Is Hindi content performing better than English?` | Multi-metric comparison by language |
| 29.6 | `What's going wrong with our publication pipeline?` | Publication rate analysis, identify problems |
| 29.7 | `Give me the executive summary` | Comprehensive overview with key KPIs and trends |
| 29.8 | `How efficient is our content operation?` | Multiple metrics: creation rate, conversion rate, throughput |

---

## Section 30: Quick Regression Checklist

After all tests, verify these fundamentals still work:

- [ ] Conversations persist and load from sidebar
- [ ] New conversation button works
- [ ] Delete conversation works
- [ ] Voice input toggle works (if supported)
- [ ] Empty state shows suggestions
- [ ] Clicking a suggestion sends it as a message
- [ ] Loading indicator shows during agent execution
- [ ] Error messages display correctly for failed requests
- [ ] Workbench close button works
- [ ] Chart type dropdown opens/closes properly
- [ ] CSV export downloads a valid file
- [ ] SQL copy button works
- [ ] Multiple browser tabs don't conflict
- [ ] Refreshing mid-query doesn't crash the UI
