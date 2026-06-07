\# Mangadvisor



Mangadvisor est un moteur de recommandation de mangas basé sur un catalogue enrichi multi-sources.



Sources utilisées :



\- Jikan (MyAnimeList)

\- AniList

\- MangaNews



Architecture :



sources → pipeline → postgres → recherche → api → ui



Stack technique :



\- Python

\- PostgreSQL + pgvector

\- Meilisearch

\- FastAPI

\- Streamlit

\- Docker



Le projet est structuré en :



apps/        API et interface  

pipelines/   pipeline data  

infra/       infrastructure Docker  

data/        datasets  

docs/        documentation

