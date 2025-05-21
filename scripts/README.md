

## Basic usage (runs all questions once with all models)

./scripts/run_queries.sh

## Run with specific models

./scripts/run_queries.sh --models openai,google,anthropic

## Test with just a few questions

./scripts/run_queries.sh --n_rows 5

## Repeat each question multiple times for statistical analysis

./scripts/run_queries.sh --repeat 3

## Close the VSCode tunnel connection after completion

./scripts/run_queries.sh --close-tunnel

## Combine options

./scripts/run_queries.sh --models openai,google --n_rows 5 --repeat 2 --close-tunnel
