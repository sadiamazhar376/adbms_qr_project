# ADBMS QR Project

A simple Django project that saves a person's details in a database and creates a
**QR code** for them. The QR code is built **by hand in pure Python** — no QR
library is used. When you scan the QR code, it opens a web page showing that
person's saved details.

This was made as a university project, so the code is kept short and easy to read.

---

## What this project does (in plain words)

1. You send a person's information (name, age, email, etc.) to the API.
2. The project saves that information in the database.
3. It generates a QR code for that person.
4. When someone scans the QR code, it opens a link that shows the person's details.

---

## Tools used

| Tool | Why it's used |
|------|----------------|
| **Python** | The programming language. |
| **Django** | Web framework that runs the server and talks to the database. |
| **Django REST Framework (DRF)** | Makes it easy to build the API and check the data. |
| **SQLite** | A simple file-based database (`db.sqlite3`). No setup needed. |

The QR code itself is made with our **own code** in `qr_api/qr_generator.py` — we do
**not** use any third-party QR library.

---

## Project structure

```
adbms_qr_project/
├── manage.py                  # Command to run Django
├── db.sqlite3                 # The database file
├── requirements.txt           # List of Python packages
├── adbms_qr_project/          # Project settings
│   ├── settings.py            # Main configuration
│   └── urls.py                # Connects "api/" to the app's URLs
└── qr_api/                    # Our app
    ├── models.py              # The "Person" table definition
    ├── serializers.py         # Checks and formats the data
    ├── views.py               # The logic for each API endpoint
    ├── qr_generator.py        # Our hand-made QR code generator
    └── urls.py                # The app's web addresses (routes)
```

---

## How the main files work

### `models.py` — the database table
Defines one table called **Person** with these fields:
`name`, `age`, `email`, `person_id`, and `city`.

### `serializers.py` — the data checker
Takes the incoming data and makes sure it is valid (for example, age must be a
number and email must look like an email). If something is wrong, it sends back
an error automatically.

### `views.py` — the brains
Has three endpoints:
- **Generate** — saves the person and returns the QR links.
- **QR Image** — returns the QR code as an SVG image.
- **Person Detail** — returns the saved person's information.

### `qr_generator.py` — the QR code maker
This is the most technical file. It builds a real, scannable QR code step by step:
1. Turns your text (a URL) into bits and bytes.
2. Adds **Reed-Solomon error correction** (so the code still scans if slightly damaged).
3. Draws the QR patterns (the corner squares, timing lines, alignment box).
4. Places the data into the grid in a zig-zag order and applies a mask.
5. Converts the final grid into an **SVG image**.

It is fixed to **QR Version 5**, error-correction **Level L**, **Mask 0** to keep
the code short and simple.

---

## Deep dive: how `qr_generator.py` works

This section explains the QR file in more detail, function by function, in simple
language. You can read it top-to-bottom to understand how a few lines of text
become a scannable QR code.

### The fixed settings (constants at the top)
```python
QR_SIZE = 37          # The QR grid is 37 x 37 squares (this is "Version 5")
DATA_CODEWORDS = 108  # How many bytes of real data the QR can hold
ERROR_CODEWORDS = 26  # Extra bytes used for error correction
MAX_INPUT_BYTES = 106 # The longest text we allow (a bit less, to leave room for headers)
```
A QR code is just a grid of black and white squares. Each square is called a
**module**. We always make the same size grid (37×37) to keep the code simple.

### Step 1 — Turn text into bits (`int_to_bits`)
A computer stores everything as **bits** (0s and 1s). This helper takes a number
and gives back its bits. Example: the number 5 in 8 bits is `[0,0,0,0,0,1,0,1]`.

### Step 2 — Math for error correction (`gf_multiply`)
QR codes can still be scanned even if part of them is dirty or damaged. This works
because of **error correction**, which needs a special kind of multiplication
called **Galois Field (GF256)** math. `gf_multiply` does that special multiply.
You don't need to fully understand the math — just know it's the tool used to
build the "backup" data.

### Step 3 — Build the error-correction recipe (`reed_solomon_generator`)
This creates a **generator polynomial** — think of it as the "recipe" that tells
us how to calculate the backup (error-correction) bytes from the real data.

### Step 4 — Create the backup bytes (`error_codewords`)
Using the recipe from Step 3, this looks at your real data and produces the 26
**error-correction codewords**. These are added after your data so a scanner can
recover the message even if some squares are unreadable.

### Step 5 — The main builder (`build_qr_matrix`)
This is the function the rest of the project calls. It ties everything together:
1. Turns your text (a URL) into bytes, and rejects it if it is too long.
2. Adds a small **header** that says "this is byte data" and how long it is.
3. Adds padding so the data fills the QR completely.
4. Packs the bits into **codewords** (bytes) and adds the error-correction bytes.
5. Creates an empty 37×37 grid and draws all the patterns onto it.
6. Returns the finished grid (a list of rows, where `True` = black square).

It also keeps a second grid called **`reserved`**. This marks which squares are
"special" (patterns) so that data bits are not accidentally drawn on top of them.

### Step 6 — Draw the corner squares and lines (`add_finder_and_timing_patterns`)
- **Finder patterns:** the three big square "eyes" in the corners. A phone uses
  these to find and line up the QR code.
- **Timing patterns:** the dashed black-and-white lines between the corners. They
  help the scanner count the rows and columns.

### Step 7 — Draw the alignment box (`add_alignment_patterns`)
A smaller 5×5 square pattern. It helps the scanner read the code correctly even
if the image is tilted or slightly bent.

### Step 8 — Write the format information (`add_format_information`)
A QR code has 15 **format bits** that tell the scanner two things: the
error-correction level (we use **L**) and the **mask** used (we use **0**).
Because our settings never change, these 15 bits are **pre-calculated** and simply
placed into the grid (they get written twice, in two locations, for safety).

### Step 9 — Fill in the data (`add_data_bits`)
Now the real data bits are placed into all the empty squares. QR codes fill in a
special **zig-zag pattern**: two columns at a time, going up, then down, then up
again, skipping any reserved squares. While placing each bit, a **mask** is
applied — `if (row + col) is even, flip the bit`. Masking spreads out the black
and white squares so the code is easier to scan (no large blank areas).

### Step 10 — Turn the grid into an image (`matrix_to_svg`)
Finally, the grid of `True`/`False` values is turned into an **SVG image** (a
text-based picture). Every `True` square becomes a small black `<rect>`
(rectangle), and a white background and border (the "quiet zone") are added so
scanners can read it. This SVG text is what the QR-image endpoint returns.

### In one sentence
Text → bits → add error-correction backup → draw the patterns → fill data in a
zig-zag with a mask → output an SVG picture you can scan. ✅

---

## How to run the project

### 1. (Optional) Create a virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # On Windows
```

### 2. Install the requirements
```bash
pip install -r requirements.txt
```

### 3. Set up the database
```bash
python manage.py migrate
```

### 4. Start the server
```bash
python manage.py runserver
```

The project will run at: **http://127.0.0.1:8000/**

---

## API endpoints (how to use it)

All endpoints start with `/api/`.

### 1. Generate a QR code — save a person
**POST** `http://127.0.0.1:8000/api/qr/generate/`

Send this JSON in the request body:
```json
{
  "name": "Sadia",
  "age": 21,
  "email": "sadia@example.com",
  "person_id": "STD-001",
  "city": "Lahore"
}
```

You get back something like:
```json
{
  "message": "Data saved and QR code generated successfully",
  "person_database_id": 1,
  "qr_contains": "http://127.0.0.1:8000/api/person/1/",
  "qr_image_url": "http://127.0.0.1:8000/api/qr/image/1/",
  "person_data_url": "http://127.0.0.1:8000/api/person/1/"
}
```

### 2. View the QR code image
**GET** `http://127.0.0.1:8000/api/qr/image/1/`

Open this in your browser to see the QR code (as an SVG image).
Scan it with your phone — it will open the person's details page.

### 3. View a person's details
**GET** `http://127.0.0.1:8000/api/person/1/`

Returns the saved information for person number 1.

---

## Quick way to test

1. Run the server (`python manage.py runserver`).
2. Use a tool like **Postman**, or the browser's DRF page, to send the POST request above.
3. Copy the `qr_image_url` from the response and open it in your browser.
4. Scan the QR code with your phone — it should open the person's details.

---

## Notes

- The database is **SQLite**, stored in the `db.sqlite3` file. Nothing extra to install.
- Because the QR generator is fixed to one size, the data (the URL) must be short.
  If the URL is too long, the API will return an error.
- This project is for learning. It is simple on purpose and not meant for production use.
