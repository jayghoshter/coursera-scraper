# Coursera Scraper

- Inputs: Coursera Domain/Topic (Such as "Data Science"). This is fuzzy selected from a list.
- Outputs: csv file with some information about all courses in the given domain
- Cache: Saves a json file with information to avoid repeated requests

# Usage

```
./script.py
```

# Notes
- Fetches only `Courses`, and not `Guided Projects`, `Degrees` or other EntityTypeDescriptions.
- Our API key only allows 1000 results at a time with filters
