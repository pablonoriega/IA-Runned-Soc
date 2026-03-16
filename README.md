# SOC Automation System

This project deploys a **Security Operations Center (SOC) simulation environment** that integrates:

- Machine Learning for incident response recommendation
- Automated workflows using **n8n**
- Containerized services using **Docker**
- A SOC operator console

The system automatically generates training data, trains a machine learning model, and deploys the entire infrastructure.

---

# Requirements

Before running the system you must install:

- **Docker Desktop**

Download it from:

https://www.docker.com/products/docker-desktop/

Make sure **Docker Desktop is installed and running** before starting the system.

---

# Quick Start (Recommended)

The easiest way to deploy the system is using the provided launcher.

## Step 1 — Run the launcher

Execute:

    dist / launcher.exe

The launcher automatically performs the following steps:

1. Generates the training dataset  
2. Trains the machine learning model  
3. Copies the trained model and the dataset into the Docker ML service  
4. Builds all Docker containers  
5. Deploys the full infrastructure  
6. Imports the **n8n workflows**  
7. Starts all services  

Once the process finishes, the SOC environment will be ready.

---

# Available Services

After deployment the following services will be available.

## n8n Automation Platform

http://localhost:5678

This service manages the automation workflows used by the SOC.

---

## SOC Console (Operator Client)

http://localhost:5173

This web interface allows SOC operators to interact with the system.

---

# Post-Deployment Configuration

After deploying the system (either automatically or manually), a small configuration step is required inside **n8n**.

Open:

    http://localhost:5678

Then complete the following configuration.

---

# Configure Ollama

The workflows use a **local LLM through Ollama**.

First install Ollama:

https://ollama.com

### Start Ollama

Ollama must be running before the workflows are executed.

Open a **CMD terminal** and run:

    ollama serve

This command starts the Ollama local API server.

### Download the required model

Then download the model used by the workflows:

    ollama pull llama3.2

### Create the Ollama credential in n8n

⚠️ **Important:**  
Credentials are not imported with workflows. Because of this, you must **create a new Ollama credential manually in n8n**.

If the credential is not created, the LLM nodes will fail.

Steps:

1. Open n8n:

       http://localhost:5678

2. Go to **Credentials**

3. Click **Create Credential**

4. Select **Ollama**

5. Configure it with:

Base URL:

    http://host.docker.internal:11434

6. Save the credential.

Then assign this credential to the Ollama nodes used in the workflows.

---

# Configure PostgreSQL Credentials

Some workflows connect to the system database through PostgreSQL nodes.

⚠️ **Important:**  
When workflows are imported into n8n, **database credentials are not imported automatically**.  
Because of this, you must **create a new PostgreSQL credential manually in n8n**.  
If this credential is not created, the workflows will fail with an error such as:

    Credential with ID "..." does not exist for type "postgres"

### Create the credential in n8n

1. Open n8n:
   
       http://localhost:5678

2. Go to **Credentials**

3. Click **Create Credential**

4. Select **PostgreSQL**

5. Use the following configuration:

Host: postgres  
Port: 5432  
Database: socdb  
User: soc  
Password: socpass  

6. Save the credential.

After creating it, assign this credential to all PostgreSQL nodes used in the workflows.

---

# Activate the Workflows

Once **Ollama and PostgreSQL credentials are configured**, the following workflows must be **activated in n8n**.

Go to the n8n interface:

    http://localhost:5678

Then activate the following workflows:

- **Process Alert**
- **Retrain Model**
- **Training Explication**
- **UpdateOperatorsShift**

The workflow **CreateAlarm** should remain **disabled**.

---

# Manual Deployment (If the launcher fails)

If the executable cannot be used, the system can be deployed manually.

---

## Step 1 — Generate the dataset

Navigate to:

    IA Model

Run:

    GenerateDataset.py

---

## Step 2 — Train the model

Inside the same folder run:

    DatasetTraining.py

This will generate the trained model:

    soc_action_recommender_rf.joblib

---

## Step 3 — Copy the trained model and the dataset

Move the file:

    soc_action_recommender_rf.joblib

to:

    Dockers/api-ml

Move the file:

    soc_dataset.csv

to:

    Dockers/api-ml/train

---

## Step 4 — Start the Docker environment

Open a **PowerShell terminal** inside:

    Dockers

Run:

    docker compose up -d --build

This command will:

- Build all required containers  
- Deploy the infrastructure  
- Start all services  

When the process finishes the system will be ready.

---

## Step 5 — Import n8n workflows

Open:

    http://localhost:5678

Import the workflows located in:

    Dockers/flows

---

## Step 6 — Configure Ollama

Install Ollama:

https://ollama.com

Open a **CMD terminal** and run:

    ollama serve

Download the required model:

    ollama pull llama3.2

Create a new **Ollama credential** in n8n with:

Base URL:

    http://host.docker.internal:11434

---

## Step 7 — Create PostgreSQL credential

Because credentials are not imported with workflows, you must create a **new PostgreSQL credential in n8n**.

Use the following configuration:

Host: postgres  
Port: 5432  
Database: socdb  
User: soc  
Password: socpass  

After creating it, assign the credential to all PostgreSQL nodes used in the workflows.

---

## Step 8 — Activate the workflows

Activate the following workflows in n8n:+

- **Process Alert**
- **Retrain Model**
- **Training Explication**
- **UpdateOperatorsShift**

Leave the workflow **CreateAlarm** disabled.

## Step 9 — Model Registration (Base Model for XAI Visualization)

Before the SOC system can display explainability information (XAI) for the machine learning model, the **base model must be manually registered in the database**. This initial registration allows the system to generate and visualize the model explanations.

The registration is performed using the executable `register_joblib_metrics.exe`, which stores the trained model (`.joblib`) together with its metadata in the model registry.

This step is required **only for the base model**. Once the first model is registered, any subsequent models generated by the system will be automatically detected and registered, and their XAI information will be available without requiring manual intervention.

### Manual Execution

To register the model manually, open a **Command Prompt (CMD)** and navigate to the directory where the executable is located:

    cd Dockers\api-ml\app\scripts

Next, configure the database connection using environment variables:

    set PG_HOST=localhost
    set PG_PORT=5432
    set PG_DB=socdb
    set PG_USER=soc
    set PG_PASS=socpass

Once the environment variables are configured, execute the registration command:

    register_joblib_metrics.exe ^
    --joblib soc_action_recommender_rf.joblib ^
    --version v1.0.0 ^
    --dataset train\soc_dataset.csv ^
    --artifact-path soc_action_recommender_rf.joblib ^
    --set-active

Parameter Description

--joblib
Path to the trained model file (.joblib).

--version
Version identifier assigned to the model.

--dataset
Dataset used during training. This is stored for traceability and reproducibility.

--artifact-path
Path to the model artifact that will be stored in the registry.

--set-active
Marks the registered model as the active version used by the system.

---

Once these steps are completed, the SOC system will be fully operational.

---

# Project Structure

.
├── IA Model  
│ ├── GenerateDataset.py  
│ ├── DatasetTraining.py  
│  
├── Dockers  
│ ├── compose.yml  
│ ├── api-ml  
│ ├── api-sim  
│ ├── flows  
│ ├── logs  
│ ├── soc-console-api  
│ └── soc-console-web  
│  
├── dist  
│ └── launcher.exe  
│  
├── LICENSE  
└── README.md  

---

# License

This project is licensed under the **MIT License**.

See the `LICENSE` file for details.