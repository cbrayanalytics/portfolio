## R Projects

### Vole Skull Classification

A statistical comparative analysis of Vole species using various morphological measurements of Vole skulls from a sample of 89 specimens. Multiple classification models were compared to predict 199 unclassified vole skulls using cross validation to determine the final accuracy.

**Results:** Final GLM achieved **91% accuracy** (Kappa = 0.83) under 10-fold CV. Classified 117 of 199 unknowns as *multiplex* and 82 as *subterraneus*.

[![Static Badge](https://img.shields.io/badge/View_R_Document-grey?logo=r&labelColor=%23276DC3)](R%20Projects/Project_1.Bray.html)

[![Static Badge](https://img.shields.io/badge/View_on_Github-grey?logo=GitHub&labelColor=%23181717)](https://github.com/cbrayanalytics/portfolio/blob/main/R%20Projects/Project_1.Bray.Rmd)


### Seed Analysis

A team-based approach to provide an accurate classification algorithm for mixed populations of dry bean seeds in central Asian countries. A comprehensive feature analysis was performed to provide the most beneficial features to be used in classification models. Multiple models were utilized for this project and accuracy was determined by determining the fiscal value of a subset from the data supplied.

**Results:** Cost-weighted polynomial LDA model selected after 10-fold CV. Predicted per-pound seed valuations for three unlabeled samples ($4.59 / $3.35 / $3.34), prioritizing dollar-impact over raw classification accuracy.


[![Static Badge](https://img.shields.io/badge/View_R_Document-grey?logo=r&labelColor=%23276DC3)](R%20Projects/FinalProject.html)

[![Static Badge](https://img.shields.io/badge/View_on_Github-grey?logo=GitHub&labelColor=%23181717)](https://github.com/cbrayanalytics/portfolio/blob/main/R%20Projects/FinalProject.rmd)




### Molecular Toxicity Classification

A binary classification of 171 chemical compounds (toxic vs. non-toxic) using molecular descriptors from the UCI toxicity-2 dataset. The full feature set contains 1,203 descriptors — Recursive Feature Elimination (RFE) with a random-forest backbone was used to reduce dimensionality before fitting Decision Tree and Random Forest models under leave-one-out cross-validation.

**Results:** RFE reduced **1,203 features to 8** without loss of cross-validated accuracy. Random Forest reached **68% test accuracy** (Kappa = 0.22) on a 2:1 imbalanced target — a 7-point absolute improvement in error over the single-tree baseline (61%). The dimensionality reduction is the headline result: comparable predictive performance from <1% of the original feature space.

[![Static Badge](https://img.shields.io/badge/View_R_Document-grey?logo=r&labelColor=%23276DC3)](R%20Projects/ToxicityAnalysis.html)

[![Static Badge](https://img.shields.io/badge/View_on_Github-grey?logo=GitHub&labelColor=%23181717)](https://github.com/cbrayanalytics/portfolio/blob/main/R%20Projects/ToxicityAnalysis.Rmd)




### Precision Agriculture Yield Analysis

A spatial causal analysis of four years (2017–2020) of GPS yield-monitor data from corn and soybean fields, asking a concrete agronomic question: when a region of the field yields poorly, is it due to a lower seeding rate or just inherently poor ground? Hundreds of thousands of geotagged harvest and seeding points across six datasets were binned into a 50×50 coordinate grid, sparse cells (<30 observations) were filtered out, and per-cell mean **Yield** and **Applied Seeding Rate** were aggregated and merged across years. **Bayesian network structure modeling** (`bnlearn`) with arc-strength scoring was then used to compare the causal influence of prior-year yield versus applied seeding rate on subsequent-year yield — repeated on rank-normalized data to suppress edge-of-field outliers.

**Results:** Across both raw and rank-normalized networks, **applied seeding rate showed strong arc strength to subsequent yield, while year-over-year yield→yield links were consistently weak** — evidence that seeding rate, not inherent field quality, is the dominant driver of yield. Outliers localized to field edges (poorer soil / crop establishment), and the one weak seeding→yield year (2018) was attributed to unmeasured factors like precipitation or wildlife.

[![Static Badge](https://img.shields.io/badge/View_Report-grey?logo=adobeacrobatreader&logoColor=white&labelColor=%23EC1C24)](R%20Projects/PrecisionAgYield.Bray.pdf)

[![Static Badge](https://img.shields.io/badge/View_on_Github-grey?logo=GitHub&labelColor=%23181717)](https://github.com/cbrayanalytics/portfolio/blob/main/R%20Projects/PrecisionAgYield.Bray.Rmd)




## Python Projects

### Auto Loan Default Prediction

The following is for a team-based approach to an auto loan default prediction algorithm. Various techniques were used for data exploration, feature extraction, and model selection. The data contained roughly 40+ features as well as incomplete data for some columns. Normalization was performed on several features and models such as XGBoost and Support Vector Machines were compared for performance by using an 80/20, Train/Test split.

**Results:** Final XGBoost model reached **78.3% test accuracy** (AUC ≈ 0.66) on a heavily imbalanced target. Feature-importance thresholding showed accuracy held within 0.1% even when reducing from 30 to 2 features — useful for downstream model-serving cost.

#### Data Preprocessing:
[![Static Badge](https://img.shields.io/badge/View_Notebook-grey?logo=Jupyter&logoColor=white&labelColor=%2344A833)](https://github.com/cbrayanalytics/portfolio/blob/main/pythonprojects/data_processing.ipynb)

#### Exploratory Data Analysis:
[![Static Badge](https://img.shields.io/badge/View_Notebook-grey?logo=Jupyter&logoColor=white&labelColor=%2344A833)](https://github.com/cbrayanalytics/portfolio/blob/main/pythonprojects/EDA.ipynb)

#### XGBoost Initial Testing:
[![Static Badge](https://img.shields.io/badge/View_Notebook-grey?logo=Jupyter&logoColor=white&labelColor=%2344A833)](https://github.com/cbrayanalytics/portfolio/blob/main/pythonprojects/XGBClassification.ipynb)


### Twitter Sentiment Analysis

A comprehensive analysis of 5,000 twitter posts that includes preprocessing, tokenization, feature reduction and classification using Stochastic Gradient Descent. Accuracy was measured using KFold Cross-Validation.

**Results:** SGD classifier reached **average F1 = 0.77** across 10 folds after feature reduction (up from 0.69 on the raw pipeline), with per-fold accuracy ranging 78–84%.

[![Static Badge](https://img.shields.io/badge/View_Notebook-grey?logo=Jupyter&logoColor=white&labelColor=%2344A833)](https://github.com/cbrayanalytics/portfolio/blob/main/pythonprojects/sanders.ipynb)


### Star Trek NLP — Preprocessing and Frequency Analysis

An exploratory NLP pipeline on dialogue from *Star Trek: Enterprise* scripts. Built a reusable text-normalization pipeline (punctuation, URL, HTML, contraction, and number-to-word handling), then ran a side-by-side comparison of **WordNet lemmatization** versus **Lancaster stemming** on the same tokenized corpus, followed by a per-episode frequency distribution.

**Results:** Composed an 8-stage normalization pipeline reusable across NLP tasks. Lemmatization preserved interpretable dictionary forms; Lancaster stemming collapsed vocabulary aggressively but produced non-word artifacts (`hundr`, `fiftyon`) — a concrete demonstration of the readability/compression tradeoff. Frequency analysis surfaced principal-cast character names as the dominant per-episode tokens, matching the show's narrative structure.

[![Static Badge](https://img.shields.io/badge/View_Notebook-grey?logo=Jupyter&logoColor=white&labelColor=%2344A833)](https://github.com/cbrayanalytics/portfolio/blob/main/pythonprojects/startrek_nlp.ipynb)
