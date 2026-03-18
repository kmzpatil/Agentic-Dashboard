import { formatPct, formatNumber, formatHours } from '../../lib/formatters';

const generateArray = (length, min, max) =>
  Array.from({ length }, () => Math.floor(Math.random() * (max - min + 1)) + min);

const generateFloatArray = (length, min, max, decimals = 1) =>
  Array.from({ length }, () => parseFloat((Math.random() * (max - min) + min).toFixed(decimals)));

const MOCK_USERS = Array.from({ length: 20 }, (_, i) => `User ${i + 1}`);
const MOCK_CHANNELS = Array.from({ length: 20 }, (_, i) => `Channel ${String.fromCharCode(65 + i)}`);

export const KPI_DEFINITIONS = [
  {
    id: 'uploaded_count',
    title: 'TOTAL UPLOADED',
    definition: 'Full count of raw video files uploaded into the pipeline.',
    formula: 'Count of Total Uploaded Videos',
    significance: 'Fundamental growth metric showing intake volume.',
    detailsData: { timeSeries: { labels: [], data: [] }, inputs: { labels: [], data: [] } },
    getValue: (kpis) => formatNumber(kpis?.uploaded_count || 0),
    getSubtitle: (kpis) => formatHours(kpis?.uploaded_duration || 0)
  },
  {
    id: 'processed_count',
    title: 'TOTAL PROCESSED',
    definition: 'Count of unique videos that have passed through the initial processing/slicing stage.',
    formula: 'Count of Total Processed Videos',
    significance: 'Measures the throughput capacity of the processing engine.',
    detailsData: { timeSeries: { labels: [], data: [] }, inputs: { labels: [], data: [] } },
    getValue: (kpis) => formatNumber(kpis?.processed_count || 0),
    getSubtitle: () => 'Videos reaching create stage'
  },
  {
    id: 'created_count',
    title: 'TOTAL CREATED',
    definition: 'Total number of individual clip assets generated from all source videos.',
    formula: 'Count of Total Created Videos',
    significance: 'Indicates the direct output volume of the creation stage.',
    detailsData: { timeSeries: { labels: [], data: [] }, inputs: { labels: [], data: [] } },
    getValue: (kpis) => formatNumber(kpis?.created_count || 0),
    getSubtitle: (kpis) => formatHours(kpis?.created_duration || 0)
  },
  {
    id: 'published_count',
    title: 'TOTAL PUBLISHED',
    definition: 'Total number of posts successfully published to one or more platforms.',
    formula: 'Count of Total Published Videos',
    significance: 'The ultimate success metric; represents final content reach.',
    detailsData: { timeSeries: { labels: [], data: [] }, inputs: { labels: [], data: [] } },
    getValue: (kpis) => formatNumber(kpis?.published_count || 0),
    getSubtitle: (kpis) => formatHours(kpis?.published_duration || 0)
  },
  {
    id: 'publish_conversion',
    title: 'PUBLISH CONVERSION RATE',
    getValue: (kpis) => formatPct(kpis?.publish_conversion_rate || 0.45),
    getSubtitle: () => 'Avg. conversion rate',
    trendData: [45, 48, 47, 52, 58, 55, 62],
    definition: 'The percentage of processed/created clips that actually end up being published.',
    formula: '(Total Published Clips / Total Created Clips) * 100',
    significance: 'This measures the direct effectiveness of the creation process. A low conversion rate indicates that a large volume of clips is being generated but discarded, signaling potential inefficiencies in what is being extracted.',
    detailsData: {
      users: { labels: MOCK_USERS, data: generateFloatArray(20, 10, 80, 1) },
      channels: { labels: MOCK_CHANNELS, data: generateFloatArray(20, 20, 90, 1) },
      timeSeries: { labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'], data: [45, 48, 47, 52, 58, 55, 62] },
      inputs: { labels: ['Interview', 'Webinar', 'Podcast', 'Tutorial', 'Vlog'], data: [65, 40, 55, 75, 30] },
      outputs: { labels: ['Reels', 'Shorts', 'TikTok', 'LinkedIn Video', 'Tweet'], data: [70, 68, 80, 45, 35] }
    }
  },
  {
    id: 'month_by_month_use_rate',
    title: 'MONTH BY MONTH USE RATE',
    getValue: () => '+12.5%',
    getSubtitle: () => 'MoM Growth',
    trendData: [2, 5, -1, 8, 10, 12, 12.5],
    definition: 'The relative growth or decline in the number of uploaded videos compared to the previous month.',
    formula: '(Current Month Uploaded Count - Previous Month Uploaded Count) / Previous Month Uploaded Count',
    significance: 'Tracks the overall adoption and usage trends over time to see if platform engagement is growing.',
    detailsData: {
      timeSeries: { labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'], data: [2, 5, -1, 8, 10, 12, 12.5] },
      channelTreemap: [
        { name: 'Channel A', value: 400 }, { name: 'Channel B', value: 300 }, { name: 'Channel C', value: 200 },
        { name: 'Channel D', value: 150 }, { name: 'Channel E', value: 100 }
      ],
      userTreemap: [
        { name: 'User 1', value: 150 }, { name: 'User 2', value: 120 }, { name: 'User 3', value: 90 },
        { name: 'User 4', value: 80 }, { name: 'User 5', value: 70 }, { name: 'User 6', value: 60 }
      ]
    }
  },
  {
    id: 'processing_efficiency',
    title: 'PROCESSING EFFICIENCY',
    getValue: (kpis) => formatPct(kpis?.processing_efficiency || 43),
    getSubtitle: () => 'Avg. time utilized',
    trendData: [35, 38, 40, 41, 42, 45, 43],
    definition: 'The ratio of the total duration of published content to the total duration of created content.',
    formula: '(Total Published Time / Total Created Time) * 100',
    significance: 'Measures temporal waste in the editing/creation stage. It highlights how much of the generated video length is actually utilized in the final published outputs.',
    detailsData: {
      users: { labels: MOCK_USERS, data: generateFloatArray(20, 20, 70, 1) },
      channels: { labels: MOCK_CHANNELS, data: generateFloatArray(20, 25, 85, 1) },
      timeSeries: { labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'], data: [35, 38, 40, 41, 42, 45, 43] },
      inputs: { labels: ['Interview', 'Webinar', 'Podcast', 'Tutorial', 'Vlog'], data: [50, 30, 45, 60, 20] },
      outputs: { labels: ['Reels', 'Shorts', 'TikTok', 'LinkedIn Video', 'Tweet'], data: [60, 55, 65, 35, 25] }
    }
  },
  {
    id: 'creation_rate',
    title: 'CREATION RATE',
    getValue: (kpis) => formatPct(kpis?.creation_rate || 0.42),
    getSubtitle: () => 'Clips per upload',
    trendData: [30, 32, 28, 35, 40, 38, 42],
    definition: 'The average number of short clips generated per single uploaded raw video.',
    formula: 'Total created count / Total uploaded count',
    significance: 'Indicates the yield of the slicing/processing engine per uploaded video.',
    detailsData: {
      inputs: { labels: ['Podcast', 'Webinar', 'Interview', 'Keynote', 'Gaming', 'Vlog', 'Tutorial'], data: [5.2, 4.8, 6.1, 3.5, 8.2, 2.1, 4.0] },
      timeSeries: { labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'], data: [3.0, 3.2, 2.8, 3.5, 4.0, 3.8, 4.2] },
      channels: { labels: MOCK_CHANNELS, data: generateFloatArray(20, 1, 10, 1) }
    }
  },
  {
    id: 'waste_index',
    title: 'WASTE INDEX',
    getValue: (kpis) => (kpis?.waste_index !== undefined ? Number(kpis.waste_index).toFixed(2) : '1.42'),
    getSubtitle: () => 'Logarithmic waste',
    trendData: [1.8, 1.7, 1.6, 1.5, 1.45, 1.4, 1.42],
    definition: 'A logarithmic scale measuring the proportion of created duration that does not get published.',
    formula: '-log10(1 - ((Total Created Duration - Total Published Duration) / Total Created duration) + 0.001)',
    significance: 'Amplifies the visibility of high-waste scenarios, helping to flag instances where the system or users are generating a massive amount of footage that is ultimately ignored.',
    detailsData: {
      channelTreemap: [
        { name: 'Channel A', value: 2500 }, { name: 'Channel B', value: 1800 }, { name: 'Channel C', value: 1200 },
        { name: 'Channel D', value: 900 }, { name: 'Channel E', value: 600 }
      ],
      teamWaste: {
        labels: ['Team Alpha', 'Team Beta', 'Team Gamma', 'Team Delta'],
        datasets: [
          { label: 'User 1', data: [500, 300, 100, 200] },
          { label: 'User 2', data: [400, 200, 150, 100] },
          { label: 'User 3', data: [300, 400, 250, 50] }
        ]
      },
      users: { labels: MOCK_USERS, data: generateFloatArray(20, 0.5, 3.0, 2) },
      channels: { labels: MOCK_CHANNELS, data: generateFloatArray(20, 0.8, 2.8, 2) }
    }
  },
  {
    id: 'upload_failure_rate',
    title: 'UPLOAD FAILURE RATE',
    getValue: () => '2.4%',
    getSubtitle: () => '0 Publishes/Upload',
    trendData: [4.1, 3.8, 3.5, 3.0, 2.8, 2.5, 2.4],
    definition: 'The severity of uploads that result in absolutely zero published clips.',
    formula: '1000 * (upload_failure_rate^1.5)',
    significance: 'Punishes consistent "dead-end" uploads. Identifying cohorts with high failure rates points directly to user training needs or systemic processing errors.',
    detailsData: {
      channels: { labels: MOCK_CHANNELS.slice(0, 15), data: generateFloatArray(15, 0.5, 8.0, 1) },
      users: { labels: MOCK_USERS.slice(0, 15), data: generateFloatArray(15, 0.2, 5.0, 1) },
      timeSeries: { labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'], data: [4.1, 3.8, 3.5, 3.0, 2.8, 2.5, 2.4] }
    }
  },
  {
    id: 'roi',
    title: 'ROI MATRIX',
    getValue: () => '1.2x',
    getSubtitle: () => 'Success vs Cost',
    trendData: [0.8, 0.9, 1.0, 1.1, 1.15, 1.18, 1.2],
    definition: 'Evaluates the computational or time cost of a clip versus its likelihood to be published.',
    formula: 'Resource Intensity (X) = Avg Created. / Overall Avg Created. | Selection Success (Y) = Conversion (Type) / Overall Conversion.',
    significance: 'Helps categorize content types. Ideally, resource-intensive clips should have high selection success.',
    detailsData: {
      users: Array.from({ length: 30 }, (_, i) => ({ x: Math.random() * 2, y: Math.random() * 2, r: 5, label: `User ${i + 1}` })),
      channels: Array.from({ length: 15 }, (_, i) => ({ x: Math.random() * 2, y: Math.random() * 2, r: 8, label: `Chan ${i + 1}` })),
      teams: Array.from({ length: 5 }, (_, i) => ({ x: Math.random() * 2, y: Math.random() * 2, r: 12, label: `Team ${i + 1}` }))
    }
  },
  {
    id: 'cdas',
    title: 'CLIP ALIGNMENT (CDAS)',
    getValue: () => '0.85',
    getSubtitle: () => 'Target: 1.0',
    trendData: [0.65, 0.70, 0.75, 0.78, 0.82, 0.84, 0.85],
    definition: 'Inspired by KL Divergence, this scores how closely the duration of the created assets aligns with the duration of the final published assets.',
    formula: '1 - (average created duration - average published duration) / (average created duration)',
    significance: 'A higher score indicates that the generated clips are already very close to their final, publishable length, implying an accurate, highly efficient initial cut.',
    detailsData: {
      inputs: { labels: ['Interview', 'Webinar', 'Podcast', 'Tutorial', 'Vlog', 'Gaming'], data: [0.85, 0.60, 0.75, 0.90, 0.45, 0.88] },
      durations: {
        labels: ['Interview', 'Webinar', 'Podcast', 'Tutorial', 'Vlog', 'Gaming'],
        datasets: [
          { label: 'Avg Created (s)', data: [60, 120, 90, 45, 180, 30] },
          { label: 'Avg Published (s)', data: [55, 65, 75, 42, 60, 28] }
        ]
      }
    }
  },
  {
    id: 'interaction_lift',
    title: 'INTERACTION LIFT',
    getValue: () => '+0.4',
    getSubtitle: () => 'Avg synergy',
    trendData: [0.1, 0.2, 0.15, 0.3, 0.35, 0.38, 0.4],
    definition: 'Measures the positive or negative correlation between two specific dimensions (e.g., Input Type and Output Type) on the publish rate.',
    formula: 'log(publish rate(dim1, dim2) / (publish rate(dim1) * publish rate(dim2)))',
    significance: 'A higher Interaction Lift Score suggests a strong positive synergy between the two dimensions. For example, determining if Interviews (input) perform exceptionally well when converted to Reels (output).',
    detailsData: {
      heatmap: (() => {
        const inputs = ['Podcast', 'Webinar', 'Interview', 'Vlog'];
        const outputs = ['Reels', 'Shorts', 'TikTok', 'LinkedIn'];
        const data = [];
        inputs.forEach((x, i) => {
          outputs.forEach((y, j) => {
            data.push({ x, y, v: (Math.random() * 2 - 1).toFixed(2) }); // values between -1 and 1
          });
        });
        return data;
      })()
    }
  },
  {
    id: 'cross_dimension_entropy',
    title: 'CROSS DIMENSION ENTROPY',
    getValue: () => '2.1',
    getSubtitle: () => 'Diversity score',
    trendData: [1.5, 1.8, 1.9, 1.8, 2.0, 2.05, 2.1],
    definition: 'A measure of the diversity of content created by each user.',
    formula: '-∑(p_ij * log2(p_ij)) , where p_ij = Total Duration(User i, Input Type j) / Total Duration(User i)',
    significance: 'Explains content variety. Users with low entropy are hyper-specialized (e.g., only uploading one specific type of video), while high entropy users upload a wide mix of content.',
    detailsData: {
      users: { labels: MOCK_USERS, data: generateFloatArray(20, 0.5, 3.5, 2) },
      userHighestShare: { labels: ['Podcast', 'Webinar', 'Interview', 'Vlog'], data: [25, 30, 20, 25] },
      teams: { labels: ['Team Alpha', 'Team Beta', 'Team Gamma', 'Team Delta'], data: generateFloatArray(4, 1.0, 3.5, 2) },
      teamHighestShare: { labels: ['Podcast', 'Webinar', 'Interview', 'Vlog'], data: [40, 20, 15, 25] }
    }
  },
  {
    id: 'publish_dependency_index',
    title: 'PUBLISH DEPENDENCY (V)',
    getValue: () => '0.45',
    getSubtitle: () => 'Cramers V',
    trendData: [0.3, 0.35, 0.4, 0.42, 0.41, 0.44, 0.45],
    definition: 'Calculates the correlation of specific categorical sectors (like language or user) with the overall publish rate.',
    formula: 'V = sqrt(x^2 / n) , where x^2 is the chi-square statistic from the contingency table.',
    significance: 'Highlights which categorical dimensions are the strongest predictors of a video actually making it to publication.',
    detailsData: {
      sectors: { labels: ['User ID', 'Input Type', 'Output Type', 'Language'], data: [0.35, 0.65, 0.82, 0.15] },
      categories: {
        userId: { labels: ['User A', 'User B', 'User C'], data: [45, 30, 70] },
        inputType: { labels: ['Podcast', 'Webinar', 'Vlog'], data: [65, 20, 40] },
        outputType: { labels: ['Reels', 'Shorts', 'LinkedIn'], data: [80, 75, 45] },
        language: { labels: ['EN', 'ES', 'FR'], data: [55, 52, 50] }
      }
    }
  },
  {
    id: 'point_biserial',
    title: 'POINT BISERIAL CORR.',
    getValue: () => '0.38',
    getSubtitle: () => 'Length vs Success',
    trendData: [0.2, 0.25, 0.3, 0.32, 0.35, 0.37, 0.38],
    definition: 'The correlation between a continuous variable (like Uploaded/Created Duration) and a binary outcome (Published or Not Published).',
    formula: 'r_pb = ((μ1 - μ0) / σ) * sqrt(pq)',
    significance: 'Determines if the initial length of an uploaded video statistically impacts its chances of being successfully published.',
    detailsData: {
      correlations: { labels: ['Created Duration', 'Uploaded Duration'], data: [0.45, -0.15] },
      createdDurations: {
        labels: ['Published', 'Not Published'],
        datasets: [{ label: 'Avg Created Duration (s)', data: [55, 120] }]
      },
      uploadedDurations: {
        labels: ['Published', 'Not Published'],
        datasets: [{ label: 'Avg Uploaded Duration (min)', data: [45, 48] }]
      }
    }
  },
  {
    id: 'multidimensional_waste',
    title: 'WASTE INTERACTION',
    getValue: () => '1.8x',
    getSubtitle: () => 'Actual / Expected',
    trendData: [1.2, 1.3, 1.5, 1.6, 1.7, 1.75, 1.8],
    definition: 'Compares the actual waste of combining two dimensions against the expected waste if those dimensions were independent.',
    formula: 'Actual Waste (input, output type) / ExpectedWaste(input, output type)',
    significance: 'Identifies toxic combinations of variables (e.g., a specific output type combined with a specific input type) that produce disproportionately high amounts of wasted video duration.',
    detailsData: {
      heatmap: (() => {
        const inputs = ['Podcast', 'Webinar', 'Interview', 'Vlog'];
        const outputs = ['Reels', 'Shorts', 'TikTok', 'LinkedIn'];
        const data = [];
        inputs.forEach((x, i) => {
          outputs.forEach((y, j) => {
            data.push({ x, y, v: (Math.random() * 3).toFixed(2) }); // values between 0 and 3
          });
        });
        return data;
      })()
    }
  },
  {
    id: 'ctas',
    title: 'TALENT ALIGNMENT',
    getValue: () => '0.76',
    getSubtitle: () => 'Channel efficiency',
    trendData: [0.6, 0.65, 0.7, 0.72, 0.71, 0.75, 0.76],
    definition: 'An efficiency metric evaluating how well a channel\'s workload is distributed among its users based on their historical publishing success.',
    formula: '∑_x [(Share(x,y) / GlobalShare(x)) * (PublishRate(x,y) / Expected PublishRate(x,y))]',
    significance: 'Identifies whether a channel is effectively utilizing its best personnel. It mathematically proves how efficiently the channel\'s workload is divided.',
    detailsData: {
      channels: { labels: MOCK_CHANNELS, data: generateFloatArray(20, 0.2, 0.95, 2) },
      userUploaded: { labels: ['User 1', 'User 2', 'User 3'], data: [50, 30, 20] },
      userPublished: { labels: ['User 1', 'User 2', 'User 3'], data: [70, 20, 10] }
    }
  },
  {
    id: 'rei',
    title: 'RELATIVE EFFICIENCY',
    getValue: () => '1.35',
    getSubtitle: () => 'Baseline adjusted',
    trendData: [1.1, 1.15, 1.2, 1.25, 1.3, 1.32, 1.35],
    definition: 'Calculates the underlying quality and potential of each individual user, adjusting for the baseline difficulty of the content types they typically upload.',
    formula: '(Created Count(user i, input j) / Created Count(user i)) * REI(User i, Input j)',
    significance: 'Prevents unfair penalization. It accounts for the possibility that a user has a low raw publish rate simply because they are tasked with uploading difficult, rarely-published video categories.',
    detailsData: {
      users: { labels: MOCK_USERS, data: generateFloatArray(20, 0.5, 2.0, 2) },
      doubleBar: {
        labels: ['Podcast', 'Interview', 'Webinar'],
        datasets: [
          { label: 'User Conversion', data: [80, 75, 45] },
          { label: 'Global Baseline', data: [65, 50, 30] }
        ]
      }
    }
  }
];
