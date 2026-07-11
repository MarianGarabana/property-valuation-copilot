# IE Background Context — Marian Garabana

Context for Claude Code / Fable 5. Read this in Phase 0 so you know the toolkit the builder (Marian) already has and which past projects to reuse. Marian holds an MSc in Business Analytics & Data Science from IE University (Madrid, class of 2026). Everything below is coursework and projects she has already done, so you can assume working familiarity, not a from-scratch explanation.

## Stack she already knows

Python, SQL (and NoSQL), Polars, pandas, scikit-learn, LightGBM-style tree models, PyTorch/Keras for deep learning, Streamlit, MLflow, Databricks, LangChain, LangGraph, Google ADK, CrewAI, Tableau, Power BI, Git/GitHub, GitHub Actions CI. Prior professional experience in tax-reporting automation and sales forecasting.

## Coursework by term (and the skills each gave her)

**Precourses**: math fundamentals, database toolkits, programming thinking.

**Term 1 (foundations)**: Statistics for Data Science, SQL Based Data Architectures I & II, Python for Data Analysis I, Modern Data Architectures I, Big Data in Operations Management, Big Data & AI in Business Strategy, Project Management, Communication Skills, plus a Datathon. Result: solid SQL, data modeling, and statistics.

**Term 2 (core ML and engineering)**:
- Machine Learning I: linear and logistic regression, segmentation, association analysis, feature engineering.
- Machine Learning II: KNN, decision trees, Naive Bayes, dimensionality reduction.
- MLOps: full lifecycle on an NYC taxi project.
- Modern Data II, NoSQL, Data Visualization (plotnine), Python II (OOP, Streamlit).
- Datathon Aqualia.

**ATT track**: Polars (basics, data manipulation, lazy evaluation). She is comfortable writing Polars ETL.

**Term 3 (advanced AI)**:
- Deep Learning: CNNs for image classification, RNNs for sentiment analysis, GANs and DCGANs, autoencoders, transfer learning and fine-tuning, image generation, a predictive-maintenance brief. She has run transfer-learning CNNs end to end in notebooks.
- Reinforcement Learning: dynamic programming, SARSA, Q-learning, DQN and beyond-DQN, policy gradients, PPO, imitation learning, RLHF.
- Generative AI: Google ADK, LangChain, LangGraph, a group project.
- Agentic AI: CrewAI hands-on labs, multi-agent orchestration.
- Cloud Data Analytics: data ingestion and transformation across a 10-session cloud course.
- Sustainable Technology.

## Past projects worth reusing (map to this build)

- **MadridRental** (`Term 2/MadridRental`): a working multi-page Streamlit app on Madrid rental data, with a Market Explorer, Property Segments, Association Rules, a Rent Predictor, and a High Rent Classifier, plus a `utils.py` and a `.streamlit` config. This is the structural base for Phase 6 (dashboard). Reuse its layout and page pattern rather than rebuilding.
- **Hospital-Prediction-System** (`Term 2/Hospital-Prediction-System`): a full MLOps repo with an initial notebook, data sampling and feature steps, experiment tracking, deployment, monitoring, CI/CD, and a client. This is the reference for Phase 7 (MLflow, drift, GitHub Actions, deploy).
- **PythonGroupAssignment** (`Term 2/PythonGroupAssignment`): has `etl/`, `api_wrapper/`, `model/`, and a Streamlit `app/`. Useful ETL and app-structure patterns for Phases 1 and 6.
- **Deep Learning notebooks** (`Term 3/Deep Learning`): transfer-learning CNN examples (cats/dogs, Simpsons, facial expression). Direct reference for Phase 4 (vision model).
- **Generative AI and Agentic AI** (`Term 3/Generative AI`, `Term 3/Agentic AI`): LangGraph, LangChain, ADK, and CrewAI material. Direct reference for Phase 5 (the copilot). Note: a Google Cloud service-account JSON exists in the GenAI folder for the free Gemini tier.
- **watt-energy-intelligence**: a Databricks energy project. Reference for the energy/ESG angle.

## How to use this

Reuse before rebuilding. When a phase overlaps one of the projects above, start from that code and adapt it. Assume Marian can read and extend anything you produce in Python, Polars, PyTorch, Streamlit, LangGraph, and MLflow, so keep explanations short and only where the logic is non-obvious. She prefers the smallest change that satisfies the request and no unrequested extras, and she wants to be asked before code comments or docs are added.

Access note: the MadridRental and Hospital-Prediction-System folders live in the `IE University` folder, not in this repo. To reuse them, either open Claude Code at the `IE University` level or copy those two folders into the project first.
