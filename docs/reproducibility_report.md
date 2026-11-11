# Reproducibility Verification Report

- **Profile**: `FULL`
- **Fixed Seed**: `20261022`
- **Anomalies Included**: `True`
- **Row Counts Identical**: `True`
- **Files Bitwise Matched**: `38/38`
- **Overall Status**: `PASS`

## Table Row Counts (Run 1 == Run 2)

| Table | Run 1 Count | Run 2 Count | Match |
| :--- | ---: | ---: | :---: |
| `action_item_evidence` | 13465 | 13465 | PASS |
| `action_items` | 5 | 5 | PASS |
| `channels` | 7 | 7 | PASS |
| `customers` | 5000 | 5000 | PASS |
| `feedback_theme_assignments` | 80326 | 80326 | PASS |
| `lifecycle_events` | 244810 | 244810 | PASS |
| `model_inputs` | 70010 | 70010 | PASS |
| `products` | 10 | 10 | PASS |
| `reviews` | 25000 | 25000 | PASS |
| `sentiment_labels` | 70010 | 70010 | PASS |
| `sentiment_shifts` | 115 | 115 | PASS |
| `support_messages` | 20000 | 20000 | PASS |
| `support_tickets` | 8000 | 8000 | PASS |
| `survey_responses` | 25010 | 25010 | PASS |
| `surveys` | 50 | 50 | PASS |
| `themes` | 12 | 12 | PASS |

## SHA-256 File Checksum Comparison

| Artifact Path | Size (Bytes) | SHA-256 (Run 1 == Run 2) |
| :--- | ---: | :--- |
| `data/ground_truth/ground_truth.csv` | 1051928 | `f924121815d10b2a7971b2de4aad554f2afd73f534dd043194d38b79e7e833e5` |
| `data/ground_truth/ground_truth.json` | 1667068 | `c1de0d801f4f869ed9160e77f8a027485eca8216e4f1053f68a57bc65438e4ee` |
| `exports/csv/action_item_evidence.csv` | 1230697 | `6a7f6400ba6821e5235199ced56cf41f9a888e217f1a507dc4e9c1eab9775e03` |
| `exports/csv/action_items.csv` | 2034 | `d1621aae92554c9045d456bdf41dd54689205363a0328bb9254de79338b1abc9` |
| `exports/csv/channels.csv` | 620 | `abe879a227553d7e7eca9b86fa99876898295ebaeaf8207f3fb2d04d25a11297` |
| `exports/csv/customers.csv` | 518116 | `22eacab53021557ecf0c8537cc2a9e1ec19a49928aa0f4bb17efcbce4344ae14` |
| `exports/csv/feedback_theme_assignments.csv` | 10229469 | `97a8d31c2a7efd549a0c8754d017d91e4bfccc1195b288d0ffb1a27393dfeab5` |
| `exports/csv/lifecycle_events.csv` | 33509116 | `d62044507493f095e3e550679697f108d3e529142428ed977bc1950604ffef36` |
| `exports/csv/model_inputs.csv` | 23550883 | `94c810a07a9dd241b724167749d61d3b5b50b5db19c84ded01e58a032443e0c6` |
| `exports/csv/products.csv` | 1062 | `14854fd271f64b2d3067375d0ba6617c93090b33b64e7ceef78291bf0e7d97c6` |
| `exports/csv/reviews.csv` | 8717332 | `211ee166111efb6b7a4d548a3065787dd78c9ece9bed66cbae7f05c3ae2c6ac2` |
| `exports/csv/sentiment_labels.csv` | 11901706 | `7288e1d086d12793523ce1e48166db43989e86fe454c1dbee158623ad11073ba` |
| `exports/csv/sentiment_shifts.csv` | 23661 | `5f103ed515ba4a0b065cf0f8d0ac380e9513c10321e13d3c55c33300cf00afde` |
| `exports/csv/support_messages.csv` | 6513295 | `bd2d57721cefe916f8fc995f84278c3132ce3f0d0bc226a278e32a0bddaafd30` |
| `exports/csv/support_tickets.csv` | 1268772 | `4367e5316c6ce9b0d42a09bc481b8bec5126c09eedb80f18cd2f3e052eef4094` |
| `exports/csv/survey_responses.csv` | 8067357 | `af828c6794dbae6134f4b8e4ea4081cc1802ad778948d202729902118f24fd36` |
| `exports/csv/surveys.csv` | 9834 | `959908553e22e9cf8f2acea9813114989c83f985d0cdadb84ea65413b7203d4c` |
| `exports/csv/themes.csv` | 7846 | `9b2cf961789d712223d7a47c28b7e811e7c129ff1dc7749d5ec22fa5386a7d05` |
| `exports/json/action_item_evidence.json` | 3735091 | `eb3cccebbf16a52024996cc2698dea10346218bc2295ca0edd763c796be8833d` |
| `exports/json/action_items.json` | 3844 | `714e00b93ef4227eb07010b6e4b6646a64454058f0d2ea9a1bdac7f95f4a847d` |
| `exports/json/channels.json` | 2002 | `400c600d6c2f6aab6375ced9546cb52e2217a6fc10f387382fc8605e2983fb71` |
| `exports/json/customers.json` | 1717484 | `810b5f0c610328cfdbd8c668fe3ff14aaab67701be2854fcefd4dfd024551b4d` |
| `exports/json/feedback_theme_assignments.json` | 29346949 | `228d4f0725ce4052baaab335ba007bd9059e01fb29205031da0e4af080356f14` |
| `exports/json/lifecycle_events.json` | 79444625 | `2b0016bbe8d457543d3f1a7fb1e13af8fbb4056e8ab2cba63632a8e1ff8bd5bd` |
| `exports/json/model_inputs.json` | 44673944 | `ac3f80f2e6d9ed8be20aa42363c4a7039d023ae226aa9d669f6c30155dbd723d` |
| `exports/json/products.json` | 3068 | `5215d9927692691bb614c7120fa6c5a0e2e54c6adf99a188fa1d95d45befd5c8` |
| `exports/json/reviews.json` | 15912192 | `51a22e7812a270e39057cd4d805df6c89a9431a3193162f3ef725d93a1bcc95a` |
| `exports/json/sentiment_labels.json` | 30804284 | `75cbf54f5061dc0ab937b2fbbbd6cf3ff43f9b54bd50076d7cd2b20d16fe487b` |
| `exports/json/sentiment_shifts.json` | 67717 | `23110a9ed2cf31f505a2649c7e6828118234f1b038a87e405b789b3ea8fcb513` |
| `exports/json/support_messages.json` | 11767548 | `b88ffd63c17b4ab630d6990c29a887012bc2b18571844bcb6616776f530edbfc` |
| `exports/json/support_tickets.json` | 3014132 | `1b9efdb3c55a6b2a8d70efcd8871313c8d26cceda11307f6ff3bd622190e1a23` |
| `exports/json/survey_responses.json` | 14907897 | `00a44283e4c77266aa48cf44fa09f235c69335e05b5acf4a998074e16d05f3a3` |
| `exports/json/surveys.json` | 23051 | `6af03acd26f011fcb4ee4dff5effde30a8ceabb16ae636e5ee4613a871948cd0` |
| `exports/json/themes.json` | 10463 | `64a10a7cf876ea2727f2e43186acbd2825690fbe496a6921a3050794b6acc619` |
| `exports/reports/evaluation_metrics.json` | 2665 | `2975f999efb029aaa36f988aa9c2b04ccc483000af559ce0fe736152d55e4754` |
| `exports/reports/validation_report.json` | 15343 | `e2218bf518cadc1ddb315bf29e9583bbb3c01742bc663fc61b7a15666fcb0a8a` |
| `exports/sql/schema.sql` | 16705 | `439a1f2ea60c86b21afd2473e5d6d93dbe2937cfba264f1ac6a10808ddb57164` |
| `exports/sql/seed.sql` | 123503056 | `fe19260dca3fb4331d1254d2d2fa13d5c42570b6cbc6cc83125721e35b305f2e` |
