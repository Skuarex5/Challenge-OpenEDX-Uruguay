import tkinter as tk
from tkinter import scrolledtext
from PIL import Image, ImageTk
from transformers import pipeline
import requests
import openai
import pytesseract
import re
from io import BytesIO
import fitz

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

GITHUB_TOKEN = "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"
REPO_OWNER = "Skuarex5"
REPO_NAME = "Chatbot-InfoLib"
openai.api_key = "sk-proj-JK0gV0W7REPBS4rwWtkjT3BlbkFJJRJFQgutMUHzjUjnsTKD"

def get_github_files():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def get_file_content(file_path):
    url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/{file_path}"
    response = requests.get(url)
    response.raise_for_status()
    return response.content

def extract_text_from_pdf(pdf_data):
    text_content = []
    pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
    for page_num in range(pdf_document.page_count):
        page = pdf_document[page_num]
        text = page.get_text()
        if text:
            text_content.append(text)
        else:
            for img in page.get_images(full=True):
                xref = img[0]
                base_image = pdf_document.extract_image(xref)
                image_bytes = base_image["image"]
                image = Image.open(BytesIO(image_bytes))
                text_content.append(pytesseract.image_to_string(image))
    pdf_document.close()
    return "\n".join(text_content)

def extract_keywords(question):
    response_es = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "Eres un asistente que extrae palabras clave en español."},
                  {"role": "user", "content": question}]
    )
    
    response_en = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "You are an assistant that extracts keywords in English."},
                  {"role": "user", "content": question}]
    )
    
    response_pr = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "Você é um assistente que extrai palavras chave em português"},
                  {"role": "user", "content": question}]
    )
    
    keywords_es = response_es['choices'][0]['message']['content'].split()
    keywords_en = response_en['choices'][0]['message']['content'].split()
    keywords_pr = response_pr['choices'][0]['message']['content'].split()
    
    return list(set(keywords_es + keywords_en))

def search_in_files(keywords, files):
    results = []
    for file in files:
        if file['type'] == 'file' and file['name'].endswith('.pdf'):
            pdf_data = get_file_content(file['path'])
            content = extract_text_from_pdf(pdf_data)
            for keyword in keywords:
                if re.search(rf'\b{keyword}\b', content, re.IGNORECASE):
                    results.append(content[:3000])
                    break
    return " ".join(results)

def generate_response(question, extracted_info):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "Eres un asistente que responde preguntas basadas en información específica."},
                  {"role": "user", "content": f"{question} {extracted_info}"}]
    )
    return response['choices'][0]['message']['content']

def summarize_with_chatgpt(question, extracted_info):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "Eres un asistente que responde preguntas basadas únicamente en la información proporcionada de los PDFs sobre edX."},
                  {"role": "user", "content": f"Pregunta: {question}. Información relevante: {extracted_info}"}]
    )
    return response['choices'][0]['message']['content']

def answer_question(question):
    try:
        files = get_github_files()
        keywords = extract_keywords(question)
        extracted_info = search_in_files(keywords, files)
        
        if extracted_info:
            return summarize_with_chatgpt(question, extracted_info)
        else:
            return "Lo siento, no encontré información relacionada con tu pregunta en los archivos disponibles."
    except Exception as e:
        return f"Ocurrió un error: {e}"

def start_chat():
    global user_name_value
    user_name_value = user_name.get()
    start_screen.pack_forget()
    load_chat_background()
    chat_screen.pack(fill=tk.BOTH, expand=True)

def load_chat_background():
    try:
        original_bg_chat = Image.open("fondochat.jpg")
        resized_bg_chat = original_bg_chat.resize((root.winfo_width(), root.winfo_height()), Image.LANCZOS)
        bg_image_chat = ImageTk.PhotoImage(resized_bg_chat)
    except Exception as e:
        print("Error al cargar el fondo del chat:", e)
        bg_image_chat = ImageTk.PhotoImage(Image.new('RGB', (root.winfo_width(), root.winfo_height()), color='blue'))

    bg_label_chat.config(image=bg_image_chat)
    bg_label_chat.image = bg_image_chat

def resize_background(event):
    load_start_background()

def load_start_background():
    new_width, new_height = root.winfo_width(), root.winfo_height()
    try:
        resized_bg = original_bg_image.resize((new_width, new_height), Image.LANCZOS)
        bg_photo = ImageTk.PhotoImage(resized_bg)
        bg_label_start.config(image=bg_photo)
        bg_label_start.image = bg_photo
    except Exception as e:
        print("Error al redimensionar el fondo de la pantalla de inicio:", e)

def add_message(text, is_bot=True):
    chat_container.configure(state='normal')
    icon = bot_icon if is_bot else user_icon
    if icon:
        chat_container.image_create(tk.END, image=icon)
    message = f" JacaBot: {text}\n\n" if is_bot else f" {user_name_value}: {text}\n\n"
    chat_container.insert(tk.END, message)
    chat_container.configure(state='disabled')
    chat_container.see(tk.END)

def send_message():
    user_text = user_entry.get()
    if user_text.lower() == "salir":
        add_message("Hasta luego.", is_bot=True)
        root.quit()
        return
    
    add_message(user_text, is_bot=False)
    response = answer_question(user_text)
    add_message(response, is_bot=True)
    user_entry.delete(0, tk.END)

root = tk.Tk()
root.title("JacaBot - Tu amigo cocodrilo")
root.geometry("800x600")
root.minsize(400, 300)
root.configure(bg="#b7f34f")

start_screen = tk.Frame(root, bg="#b7f34f")
bg_label_start = tk.Label(start_screen)
bg_label_start.place(relwidth=1, relheight=1)
start_screen.pack(fill=tk.BOTH, expand=True)

try:
    bot_icon_image = Image.open("cocodrilo.jpg").resize((30, 30), Image.LANCZOS)
    bot_icon = ImageTk.PhotoImage(bot_icon_image)
except Exception as e:
    print("Error al cargar el ícono del bot:", e)
    bot_icon = None

try:
    user_icon_image = Image.open("flecha.jpg").resize((30, 30), Image.LANCZOS)
    user_icon = ImageTk.PhotoImage(user_icon_image)
except Exception as e:
    print("Error al cargar el ícono del usuario:", e)
    user_icon = None

try:
    original_bg_image = Image.open("fondo.jpg")
except Exception as e:
    print("Error al cargar la imagen de fondo:", e)
    original_bg_image = Image.new('RGB', (1920, 1080), color='green')

user_name_value = "Gabriel"

tk.Label(start_screen, text="Ingrese su nombre:", font=("Helvetica", 14), bg="#b7f34f").pack(pady=10)
user_name = tk.StringVar(value="")
tk.Entry(start_screen, textvariable=user_name, font=("Helvetica", 12)).pack(pady=5)

start_button = tk.Button(start_screen, text="Iniciar Chat", font=("Helvetica", 14), command=start_chat)
start_button.pack(pady=20)

chat_screen = tk.Frame(root, bg="#b7f34f")
bg_label_chat = tk.Label(chat_screen)
bg_label_chat.place(relwidth=1, relheight=1)

chat_container = scrolledtext.ScrolledText(chat_screen, wrap=tk.WORD, state='disabled', bg="#FFF", font=("Arial", 10))
chat_container.place(relx=0.05, rely=0.05, relwidth=0.9, relheight=0.75)

user_entry = tk.Entry(chat_screen, font=("Helvetica", 12))
user_entry.place(relx=0.05, rely=0.85, relwidth=0.7, height=30)
user_entry.bind("<Return>", lambda event: send_message())

send_button = tk.Button(chat_screen, text="Enviar", font=("Helvetica", 12), command=send_message)
send_button.place(relx=0.8, rely=0.85, relwidth=0.15, height=30)

add_message("¡Hola! Soy JacaBot, ¿en qué puedo ayudarte?", is_bot=True)

root.bind("<Configure>", resize_background)

root.mainloop()
