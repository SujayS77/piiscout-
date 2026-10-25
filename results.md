Evaluation on 600 samples containing 1116 labelled PII items.

Overall (micro-averaged over every PII item)

| Method | Precision | Recall | F1 | Recall on hard variants | ms / sample |
|---|---|---|---|---|---|
| rule | 0.948 | 0.543 | 0.691 | 0.000 | 0.03 |
| ner | 0.648 | 0.212 | 0.320 | 0.081 | 10.21 |
| hybrid | 0.856 | 0.755 | 0.802 | 0.081 | 5.64 |

Per type (precision / recall / F1)

| Type | rule | ner | hybrid |
|---|---|---|---|
| NAME | 0.00 / 0.00 / 0.00 | 0.65 / 0.58 / 0.61 | 0.68 / 0.58 / 0.63 |
| AADHAAR | 0.97 / 0.84 / 0.90 | 0.00 / 0.00 / 0.00 | 0.97 / 0.84 / 0.90 |
| PAN | 1.00 / 0.83 / 0.91 | 0.00 / 0.00 / 0.00 | 1.00 / 0.83 / 0.91 |
| PHONE | 0.83 / 0.79 / 0.81 | 0.00 / 0.00 / 0.00 | 0.83 / 0.79 / 0.81 |
| EMAIL | 1.00 / 1.00 / 1.00 | 0.00 / 0.00 / 0.00 | 1.00 / 1.00 / 1.00 |
| UPI | 1.00 / 0.86 / 0.92 | 0.00 / 0.00 / 0.00 | 1.00 / 0.86 / 0.92 |
