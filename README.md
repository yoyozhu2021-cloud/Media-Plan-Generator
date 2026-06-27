# Media Plan Google Sheet Generator

Python automation for creating a formatted Google Sheet media plan from a client brief JSON.

## Run

```powershell
pip install -r requirements.txt
python main.py sample_client_input.json
```

By default, the script looks for a Google service account key at:

```text
service_account.json
```

You can also pass another key path:

```powershell
python main.py sample_client_input.json --credentials path\to\service_account.json
```

## Google Setup

1. Create a Google Cloud project.
2. Enable the Google Sheets API.
3. Create a service account.
4. Download the service account JSON key.
5. Save it as `service_account.json` in this project folder.

## Client Brief Format

Required:

- `client_name`
- `market`
- `total_budget_rmb`

Optional:

- `selected_platforms`: platforms to highlight yellow.
- `platform_budgets_rmb`: exact RMB budget per platform.
- `platform_budget_percentages`: budget percentage per platform.
- `benchmarks`: override CPC, CTR, or CPR defaults.

If no platform budgets or percentages are provided, the total budget is split evenly across selected platforms.

## Output Columns

1. Channel
2. Ad Platform
3. Budget Allocation (RMB)
4. Budget %
5. Estimated Clicks
6. Estimated Impressions
7. Estimated CTR
8. Estimated Avg. CPC (RMB)
9. Estimated Avg. CPR (RMB)
10. Estimated Registrations

## Included Channel Groups

- Search Advertising
  - Google Keyword Search
  - Yandex
  - Google PMax
- Display Ad Network
  - Google Remarketing
- Social Media Advertising
  - Facebook & IG Website Traffic
  - Facebook & IG Lead Ads
  - TikTok
  - LinkedIn Lead Ads

## Default Benchmarks

| Platform | CPC | CTR | CPR |
| --- | ---: | ---: | ---: |
| Google Keyword Search | 8 | 2% | 120 |
| Yandex | 6 | 2% | 120 |
| Google PMax | 3 | 3% | 110 |
| Google Remarketing | 2 | 1.2% | 120 |
| Facebook & IG Website Traffic | 4 | 0.6% | 200 |
| Facebook & IG Lead Ads | 4 | 0.6% | 100 |
| TikTok | 3 | 0.6% | 150 |
| LinkedIn Lead Ads | 28 | 0.6% | 800 |

## Sheet Formatting

The generated Google Sheet includes:

- Green header row
- Yellow highlight for selected ad platforms
- RMB currency formatting
- Percentage formatting
- Thousands separator
- Merged cells for channel groups
- Final Total row with formulas
