# 📘 Mint Maths Question Generator

**Mint Maths** is a web app that generates random past exam questions for practice.  
Users can filter by year, topic, or paper (calculator/non-calculator), and instantly download a custom PDF containing both the selected questions and their corresponding solutions.

---

## 🚀 Features

- 🎯 **Smart Question Selection**
  - Randomized question generator with optional filters for year, topic, and paper.
- 🧮 **Dynamic PDF Builder**
  - Automatically compiles a clean, mint-styled PDF containing your chosen questions and their solutions.
- 🧠 **Instant Practice Mode**
  - View questions directly in the app, then download your complete practice set.
- 💾 **Cached Storage**
  - Caches previously generated PDFs for faster performance.
- 📱 **Mobile-Friendly**
  - Works smoothly on both desktop and mobile browsers.

---

## 🧩 Tech Stack

| Component | Technology |
|------------|-------------|
| Backend | Flask (Python 3.11) |
| Frontend | Streamlit (for UI) |
| PDF Generation | ReportLab + PyPDF |
| Data Source | `.ods` spreadsheet with question metadata |
| Hosting | Fly.io (Dockerized) |
| Styling | Mint green theme (custom CSS) |

---

## 🗂️ Project Structure

