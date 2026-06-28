# Formula TV — ვიდეოების გადმოწერა

სკრიპტი გადმოწერს სერიალის "ჩემი ცოლის დაქალები" (და სხვა Formula TV სერიალების) ეპიზოდებს უშუალოდ CDN-დან.

## მოთხოვნები

- Python 3.9+
- `requests`

```powershell
pip install requests
```

## გამოყენება

```powershell
# ყველა სეზონი, უმაღლესი ხელმისაწვდომი ხარისხი
python download_formula.py

# კონკრეტული სეზონი (seasonId 1)
python download_formula.py --season 1

# რამდენიმე სეზონი ერთად
python download_formula.py --season 1 2 3

# ხარისხი (1080p | 720p | 360p)
python download_formula.py --season 18 --quality 720p

# გადმოწერის საქაღალდე
python download_formula.py --out D:\Videos\CHCD
```

## სტრუქტურა

ფაილები ინახება:

```
<out>/სეზონი 1/სერია 1 [720p].mp4
<out>/სეზონი 1/სერია 2 [720p].mp4
...
```

შენიშვნა: სკრიპტი ავტომატურად ამოწმებს უკვე გადმოწერილ ფაილებს, აქვს resume (Range) მხარდაჭერა და თავიდან ცდის წყვეტისას.

## API რესურსები

- სეზონები: `https://mw-api.formula.ge/formula/api/tvseries/{seriesId}`
- ეპიზოდები: `https://mw-api.formula.ge/formula/api/tvseries/episodes/{seasonInternalId}`
- ეპიზოდის დეტალები: `https://mw-api.formula.ge/formula/api/tvseries/e/{episodeId}`
