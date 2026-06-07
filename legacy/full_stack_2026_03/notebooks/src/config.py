# 📂 Configuration générale pour le projet Manga

# Gestion des avertissements
import warnings  # Gestion des avertissements inutiles

# Manipulation des fichiers et répertoires
import os  # Interagir avec le système de fichiers
import shutil  # Manipulation avancée des fichiers et répertoires
from pathlib import Path  # Gestion multiplateforme des chemins de fichiers
import ast  # Ajouté pour manipuler des structures Python à partir de chaînes

# Manipulation et analyse des données
import json  # Lecture et écriture des données au format JSON
import numpy as np  # Calculs numériques et gestion des tableaux
import pandas as pd  # Manipulation et analyse des données sous forme de DataFrames
import polars as pl  # Alternative performante pour manipuler des données tabulaires

# Visualisation des données
import matplotlib.pyplot as plt  # Création de graphiques statiques
import plotly.express as px  # Visualisations interactives simples
import plotly.graph_objects as go  # Graphiques interactifs personnalisés
import seaborn as sns  # Visualisations graphiques esthétiques

# Requêtes HTTP et gestion des erreurs
import requests  # Requêtes HTTP pour interagir avec les API
from bs4 import BeautifulSoup  # Analyse et extraction des données HTML
from retrying import retry  # Pour mettre en œuvre des mécanismes de réessai en cas d'échec des requêtes

# Gestion des événements et des logs
from loguru import logger  # Gestion avancée des logs
import sys  # Utilisé pour afficher les logs dans le notebook

# Divers utilitaires
from skimpy import skim  # Vue d'ensemble rapide et visuelle des DataFrames
from tqdm import tqdm  # Affichage de barres de progression dans les boucles
from typing import List, Tuple, Union  # Types pour annotations, clarté et documentation
import time  # Gestion des pauses et des intervalles entre les requêtes

# 📌 Répertoire de base
BASE_DIR = Path(__file__).resolve().parent.parent

# 📂 Répertoires principaux
CONFIG = {
    "base_directory": BASE_DIR,
    "data_directory": BASE_DIR / "data",
    "raw_directory": BASE_DIR / "data/raw",
    "processed_directory": BASE_DIR / "data/processed",
    "outputs_directory": BASE_DIR / "outputs",
    "logs_directory": BASE_DIR / "logs",
    "notebooks_directory": BASE_DIR / "notebooks",
    "scripts_directory": BASE_DIR / "scripts",
    "docs_directory": BASE_DIR / "docs",
    "tests_directory": BASE_DIR / "tests",
}

# 🔧 Création des répertoires
for key, path in CONFIG.items():
    if "directory" in key:
        path.mkdir(parents=True, exist_ok=True)

# 🖋️ Initialisation des logs généraux (par défaut)
logger.remove()  # Supprimer les handlers existants pour éviter les duplications

# Ajouter un handler global pour le projet
logger.add(
    CONFIG["logs_directory"] / "project.log",
    format="{time} {level} {message}",
    level="INFO",  # Niveau minimal des logs à enregistrer
    rotation="10 MB",  # Rotation des fichiers pour éviter des logs trop volumineux
    compression="zip"  # Compresse les anciens fichiers
)

# Fonction d'initialisation des logs spécifiques pour chaque notebook
def init_notebook_logs(notebook_name: str):
    """
    Initialise un fichier log spécifique pour un notebook donné dans le dossier des logs.
    Remplace les handlers existants pour éviter les doublons.
    
    Args:
        notebook_name (str): Nom du notebook (sans extension).
    """
    logger.remove()  # Supprime tous les handlers actuels
    logger.add(
        CONFIG["logs_directory"] / f"{notebook_name}_log.log",
        format="{time} {level} {message}",
        level="INFO"
    )
    logger.info(f"Log démarré pour le notebook : {notebook_name}")

# 🎨 Style des graphiques
sns.set(style="whitegrid")  # Appliquer un style global pour Seaborn

# ⚙️ Configurations pandas pour l'affichage
pd.set_option('display.max_columns', None)  # Affiche toutes les colonnes
pd.set_option('display.max_rows', 100)  # Limite l'affichage à 100 lignes
pd.set_option('display.width', 275)  # Évite les retours à la ligne dans les DataFrames

# 🧹 Nettoyage des warnings inutiles
warnings.filterwarnings("ignore", category=UserWarning, module="bs4")  # Ignorer les warnings BeautifulSoup

logger.info("Fichier config.py mis à jour et prêt à l'emploi.")
