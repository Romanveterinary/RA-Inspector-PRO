import flet as ft
import os
import datetime
import base64
import requests
import json
import traceback

# --- БЕЗПЕЧНІ ШЛЯХИ ДЛЯ ПК ТА АНДРОЇД ---
safe_dir = os.environ.get("FLET_APP_STORAGE", ".") 
KEY_FILE = os.path.join(safe_dir, "api_key_frozen.txt")
PROMPTS_FILE = os.path.join(safe_dir, "frozen_prompts.json") 
REPORTS_DIR = "/storage/emulated/0/Download"
PHOTOS_DIR = os.path.join(safe_dir, "photos")

try:
    if not os.path.exists(REPORTS_DIR): REPORTS_DIR = safe_dir
except: REPORTS_DIR = safe_dir

try:
    if not os.path.exists(PHOTOS_DIR): os.makedirs(PHOTOS_DIR, exist_ok=True)
except: pass

IMPORT_DIR = os.path.join(REPORTS_DIR, "Frozen_Prompts_Import")
try:
    if not os.path.exists(IMPORT_DIR): os.makedirs(IMPORT_DIR, exist_ok=True)
except: pass

# ==========================================
# 🧠 БАЗА ЗНАНЬ ШІ (РОЗШИРЕНІ ВІДДІЛИ)
# ==========================================
DEFAULT_PROMPTS = {
    "🧊 Морозильна скриня (Напівфабрикати)": "Наявність снігу/льоду в пакетах: ознака дефростації. Викладка: чи пакети лежать акуратно, чи накидані горою? Порадь використовувати розділювачі.",
    "🥛 Молочний відділ": "Зверни увагу на температурний режим. Шукай здуті упаковки (бомбаж), конденсат, ознаки розшарування продукту. Перевір правильність товарного сусідства.",
    "🥩 Ковбасний відділ": "Оціни колір продукції, відсутність завітрювання на зрізах, цілісність вакуумної упаковки. Перевір відсутність сторонньої рідини в упаковці.",
    "🍎 Фрукти": "Шукай ознаки гниття, плісняви, зморщування. Зверни увагу на наявність мошок (дрозофіл), чистоту ящиків та загальну привабливість викладки.",
    "🥦 Овочі": "Оціни чистоту, відсутність гнилі, проростання (наприклад, у картоплі чи цибулі), зморщування. Овочі мають виглядати свіжими та презентабельними.",
    "🌾 Крупи та бакалія": "Перевір цілісність упаковки (щоб не розсипалось), відсутність слідів шкідників (харчової молі, жучків), відсутність вологи чи комкування всередині пакетів.",
    "🍷 Алкоголь": "Оціни чистоту пляшок (відсутність пилу), рівність викладки (етикетки обличчям до покупця), наявність та цілісність акцизних марок.",
    "🥟 Упаковка та Штрих-коди": "Маркування: чи видно етикетки і штрих-коди лицьовою стороною до покупця? Чи вони читабельні? Чи немає пошкоджень тари?",
    "👩‍🍳 Персонал (Одяг/Гігієна)": "Одяг: наявність фірмового одягу, чистого фартуха, головного убору (волосся має бути сховане) та рукавичок.",
    "🧹 Загальний санітарний стан": "Освітлення та чистота: чи чисте скло вітрин? Чи достатньо світла? Чи чиста підлога та полиці?",
    "🏪 Змішана зона (Міні-маркет / Все разом)": """КОМПЛЕКСНИЙ АУДИТ МАГАЗИНУ. На фото одразу кілька зон. 
Роби детальний розбір всього, що бачиш:
1. Температура в ЗАЛІ (якщо вище +25°C - вкажи на ризик поломки холодильників та псування шоколаду/кондитерки).
2. Холодильники (наявність льоду, правильність викладки).
3. Товарне сусідство (чи не лежить сире м'ясо/риба біля готових продуктів - це грубе порушення!).
4. Мерчандайзинг (оціни хаос, дай поради по перестановці товару для збільшення продажів).
5. Персонал та загальна санітарія (пилюка, бруд на підлозі)."""
}

def load_prompts():
    prompts = DEFAULT_PROMPTS.copy()
    try:
        if os.path.exists(PROMPTS_FILE):
            with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                prompts.update(loaded)
    except: pass
    return prompts

def save_prompts(prompts_dict):
    try:
        with open(PROMPTS_FILE, "w", encoding="utf-8") as f:
            json.dump(prompts_dict, f, ensure_ascii=False, indent=2)
    except: pass

user_prompts = load_prompts()

# ==========================================
# ⚙️ РОБОТА З API КЛЮЧЕМ
# ==========================================
DEFAULT_API_KEY = "" # ЗАЛИШИВ ПОРОЖНІМ ДЛЯ БЕЗПЕКИ НА GITHUB

def get_saved_api_key():
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "r") as f:
            return f.read().strip()
    return None

def save_api_key_to_file(key):
    with open(KEY_FILE, "w") as f:
        f.write(key)

# ==========================================
# ГОЛОВНА ФУНКЦІЯ ДОДАТКА
# ==========================================
def main(page: ft.Page):
    try:
        page.title = "RA-Inspector"
        page.window_width = 450
        page.window_height = 850
        page.scroll = ft.ScrollMode.AUTO
        page.theme_mode = ft.ThemeMode.LIGHT
        page.padding = 10

        selected_media_paths = [] 

        def show_snack(msg, color="green"):
            page.snack_bar = ft.SnackBar(content=ft.Text(msg), bgcolor=color)
            page.snack_bar.open = True
            page.update()
        
        api_key_input = ft.TextField(label="Вставте ваш Gemini API Key сюди", width=300, password=True, can_reveal_password=True)
        
        def save_api_key(e):
            save_api_key_to_file(api_key_input.value)
            settings_dialog.open = False
            show_snack("✅ API Ключ успішно збережено!", "green")

        settings_dialog = ft.AlertDialog(
            title=ft.Text("Налаштування API", weight="bold"),
            content=ft.Column([
                ft.Text("Введіть секретний ключ від Google Gemini:", size=12, color="grey"),
                api_key_input
            ], tight=True),
            actions=[ft.TextButton("Зберегти", on_click=save_api_key)]
        )
        page.overlay.append(settings_dialog)

        def open_settings(e):
            saved_key = get_saved_api_key()
            api_key_input.value = saved_key if saved_key else DEFAULT_API_KEY
            settings_dialog.open = True
            page.update()

        # ==========================================
        # ВКЛАДКА 1: АУДИТ (ОСНОВНА)
        # ==========================================
        title_row = ft.Row([
           ft.Text("☀️ RA-Inspector PRO", size=20, weight=ft.FontWeight.BOLD, color=ft.colors.RED_900),
            ft.TextButton("⚙️ ШІ-Ключ", on_click=open_settings, tooltip="Налаштування API")
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        
        media_row = ft.Row(wrap=True, scroll=ft.ScrollMode.AUTO, height=120)
        
        def get_category_options():
            return [ft.dropdown.Option(k) for k in user_prompts.keys()]

        temp_input = ft.TextField(label="T °C", width=95)
        
        def on_zone_change(e):
            if "Змішана" in object_dropdown.value:
                temp_input.label = "T °C в залі"
                temp_input.hint_text = "+25"
                temp_input.bgcolor = ft.colors.ORANGE_50
            else:
                temp_input.label = "T °C облад."
                temp_input.hint_text = "-18"
                temp_input.bgcolor = None
            page.update()

        object_dropdown = ft.Dropdown(
            label="Зона аудиту", 
            options=get_category_options(), 
            value=list(user_prompts.keys())[0], 
            expand=True,
            on_change=on_zone_change
        )
        on_zone_change(None) 
        
        inspector_comment = ft.TextField(label="Коментар аудитора", expand=True, hint_text="Наприклад: Знайшов злиплі пельмені...")
        
        risk_indicator = ft.Container(
            content=ft.Text("ОЦІНКА МАГАЗИНУ: НЕ ПРОВЕДЕНО", color=ft.colors.WHITE, weight=ft.FontWeight.BOLD),
            bgcolor=ft.colors.GREY, padding=10, border_radius=5, alignment=ft.alignment.center
        )
        
        ai_response_text = ft.Markdown(value="*Очікування медіафайлів...*", selectable=True, extension_set="gitHubWeb")

        # --- ФУНКЦІЇ КАМЕРИ ТА ВІДЕО ---
        def pick_file_result(e):
            try:
                if e.files:
                    for f in e.files:
                        if not f.path: continue
                        file_path = f.path
                        selected_media_paths.append(file_path)
                        
                        if file_path.lower().endswith(('.mp4', '.mov', '.avi', '.webm')):
                            media_row.controls.append(
                                ft.Container(
                                    content=ft.Column([ft.Icon(ft.icons.VIDEO_FILE, size=40, color="blue"), ft.Text("ВІДЕО", size=10, weight="bold")], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                    width=100, height=100, bgcolor=ft.colors.BLUE_50, border_radius=5
                                )
                            )
                        else:
                            media_row.controls.append(ft.Image(src=file_path, width=100, height=100, fit=ft.ImageFit.COVER, border_radius=5))
                    page.update()
            except Exception as ex:
                show_snack(f"Помилка вибору файлу: {str(ex)}", "red")

        file_picker = ft.FilePicker()
        file_picker.on_result = pick_file_result
        page.overlay.append(file_picker)

        def trigger_media_picker(e):
            file_picker.pick_files(allow_multiple=True, file_type=ft.FilePickerFileType.MEDIA)

        # --- ЗАПИТ ДО ШІ (ВНУТРІШНІЙ АУДИТ) ---
        def perform_analysis(e):
            if "пиво будеш" in inspector_comment.value.lower():
                risk_indicator.bgcolor = ft.colors.BLUE_700
                risk_indicator.content.value = "🍻 ПИВНИЙ ПАТРУЛЬ НА МІСЦІ!"
                ai_response_text.value = "## 🍻 без Романа НІ!!!"
                page.update()
                return

            current_key = get_saved_api_key() or DEFAULT_API_KEY
            if not current_key.strip():
                ai_response_text.value = "❌ Будь ласка, вставте свій API-ключ у Налаштуваннях (⚙️)."
                page.update()
                return

            if not selected_media_paths:
                ai_response_text.value = "❌ Додайте хоча б одне фото або відео."
                page.update()
                return
                
            ai_response_text.value = "⏳ *Штучний інтелект аналізує відповідність корпоративним стандартам...*"
            page.update()

            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={current_key}"
                
                parts = []
                for path in selected_media_paths:
                    file_size_mb = os.path.getsize(path) / (1024 * 1024)
                    if file_size_mb > 19:
                        ai_response_text.value = f"❌ ВІДМОВА: Файл занадто великий ({file_size_mb:.1f} МБ). Обмеження: 19 МБ."
                        page.update()
                        return

                    with open(path, "rb") as f:
                        b64_data = base64.b64encode(f.read()).decode("utf-8")
                        mime_type = "image/jpeg"
                        if path.lower().endswith(('.mp4', '.mov', '.avi', '.webm')):
                            mime_type = "video/mp4"
                        elif path.lower().endswith('.png'):
                            mime_type = "image/png"
                        parts.append({"inline_data": {"mime_type": mime_type, "data": b64_data}})
                
                category = object_dropdown.value
                custom_rule = user_prompts.get(category, "Проведи загальний огляд.")

                system_instruction = f"""
                Ти — суворий внутрішній корпоративний аудитор та експерт з якості мережі магазинів "MULTI_COOK".
                Твоя мета: виявити порушення внутрішніх стандартів, захистити споживача та вберегти бренд виробника від репутаційних втрат.
                
                ❗️ ПРАВИЛА ДЛЯ ПОТОЧНОЇ ЗОНИ АУДИТУ ({category}):
                {custom_rule}
                
                📋 КОРПОРАТИВНИЙ СТАНДАРТ ТА ПРАВИЛА ТОРГІВЛІ: 
                У разі виявлення БУДЬ-ЯКИХ порушень (бруд, дефростація, погане товарне сусідство, відсутність цінників) ти ЗОБОВ'ЯЗАНИЙ вказати на це.
                Посилайся на внутрішні стандарти мережі та базові правила торгівлі харчовими продуктами. Вказуй на наслідки для бізнесу: списання товару, втрата лояльності покупців, внутрішні дисциплінарні стягнення для персоналу.
                НЕ згадуй державні органи чи Держпродспоживслужбу, це виключно ВНУТРІШНІЙ аудит фірми.
                
                Завершуй звіт визначенням РИЗИКУ ДЛЯ БІЗНЕСУ: [РИЗИК_ЗЕЛЕНИЙ] (все ідеально, стандарти дотримано), [РИЗИК_ЖОВТИЙ] (є порушення, ризик втрати продажів), [РИЗИК_ЧЕРВОНИЙ] (критичні порушення якості, ризик псування товару).
                Відповідай суворою, професійною діловою мовою у форматі акту внутрішньої перевірки.
                """

                temp_context = "Температура в торговому залі (впливає на умови зберігання та роботу обладнання)" if "Змішана" in category else "Температура всередині холодильного обладнання"

                prompt = f"""
                Проаналізуй усі надані фото та відео. 
                - {temp_context}: {temp_input.value} °C
                - ⚠️ ОФІЦІЙНИЙ КОМЕНТАР АУДИТОРА НА МІСЦІ: {inspector_comment.value}
                
                ❗️ НАЙВИЩИЙ ПРІОРИТЕТ: Коментар аудитора є АБСОЛЮТНОЮ ІСТИНОЮ. Ти зобов'язаний повністю погодитися з оцінкою аудитора, підтвердити його спостереження та будувати свій висновок безпосередньо спираючись на його слова. Людина на місці бачить краще!
                
                Склади детальний акт корпоративної перевірки.
                """
                
                parts.append({"text": prompt})
                
                payload = {
                    "system_instruction": {"parts": [{"text": system_instruction}]},
                    "contents": [{"parts": parts}]
                }
                
                resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
                
                if resp.status_code != 200:
                    ai_response_text.value = f"❌ Помилка API ({resp.status_code}): Перевірте підключення до Інтернету або змініть ключ."
                    page.update()
                    return
                    
                result_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                
                if "[РИЗИК_ЗЕЛЕНИЙ]" in result_text:
                    risk_indicator.bgcolor = ft.colors.GREEN
                    risk_indicator.content.value = "ВНУТРІШНІЙ АУДИТ: ВІДМІННО"
                elif "[РИЗИК_ЖОВТИЙ]" in result_text:
                    risk_indicator.bgcolor = ft.colors.YELLOW_800
                    risk_indicator.content.value = "ВНУТРІШНІЙ АУДИТ: Є ПОРУШЕННЯ"
                elif "[РИЗИК_ЧЕРВОНИЙ]" in result_text:
                    risk_indicator.bgcolor = ft.colors.RED
                    risk_indicator.content.value = "ВНУТРІШНІЙ АУДИТ: КРИТИЧНІ ПОРУШЕННЯ"

                result_text = result_text.replace("[РИЗИК_ЗЕЛЕНИЙ]", "").replace("[РИЗИК_ЖОВТИЙ]", "").replace("[РИЗИК_ЧЕРВОНИЙ]", "")
                ai_response_text.value = result_text.strip()
                page.update()
                
            except Exception as ex:
                ai_response_text.value = f"❌ Помилка аналізу: {str(ex)}"
                page.update()

        def generate_act(e):
            if "Очікування" in ai_response_text.value or not ai_response_text.value:
                show_snack("Спочатку проведіть аналіз!", "red")
                return
                
            current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"MultiCook_Audit_{current_time}.html"
            filepath = os.path.join(REPORTS_DIR, filename)
            
            media_html = ""
            for path in selected_media_paths:
                try:
                    if path.lower().endswith(('.mp4', '.mov', '.avi', '.webm')):
                        media_html += f"<div style='margin: 10px; padding: 10px; background: #e3f2fd; border-radius: 5px; display: inline-block;'><b>[🎥 Прикріплено відеодоказ: {os.path.basename(path)}]</b></div><br>"
                    else:
                        with open(path, "rb") as img_file:
                            b64_str = base64.b64encode(img_file.read()).decode('utf-8')
                            media_html += f"<img src='data:image/jpeg;base64,{b64_str}' style='max-width: 300px; margin: 10px; border-radius: 5px; border: 1px solid #ccc;'><br>"
                except: pass

            temp_label_html = "Температура в торговому залі:" if "Змішана" in object_dropdown.value else "Температура обладнання:"

            html_content = f"""
            <html>
            <head><meta charset='utf-8'><title>Акт Внутрішнього Аудиту MULTI_COOK</title>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 20px; max-width: 800px; margin: auto; }}
                    h1 {{ color: #b71c1c; text-align: center; border-bottom: 2px solid #b71c1c; padding-bottom: 10px; }}
                    .info-block {{ background-color: #ffebee; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 5px solid #b71c1c; }}
                    .ai-text {{ white-space: pre-wrap; line-height: 1.6; font-size: 15px; }}
                    .photos {{ text-align: center; }}
                    .law-section {{ background-color: #fff3e0; padding: 10px; border-left: 4px solid #ff9800; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <h1>АКТ ВНУТРІШНЬОГО АУДИТУ «MULTI_COOK»</h1>
                <div class="info-block">
                    <p><strong>Дата та час проведення:</strong> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>Об'єкт перевірки (Зона):</strong> {object_dropdown.value}</p>
                    <p><strong>{temp_label_html}</strong> {temp_input.value} °C</p>
                    <p><strong>Висновки аудитора на місці:</strong> {inspector_comment.value}</p>
                    <p style="font-size: 18px;"><strong>РІШЕННЯ: <span style="color: red;">{risk_indicator.content.value}</span></strong></p>
                </div>
                <h2>Фото та відеофіксація матеріалів перевірки:</h2><div class="photos">{media_html}</div>
                <h2>Експертний висновок аудитора:</h2><div class="ai-text law-section">{ai_response_text.value}</div>
            </body></html>
            """
            
            try:
                with open(filepath, "w", encoding="utf-8") as file:
                    file.write(html_content)
                ai_response_text.value += f"\n\n---\n**✅ АКТ ЗБЕРЕЖЕНО!**\nФайл `{filename}` створено в Завантаженнях."
                show_snack("✅ Акт аудиту збережено на телефон!", "green")
            except Exception as err:
                ai_response_text.value += f"\n\n---\n**❌ Помилка збереження акту:** {str(err)}"
            page.update()

        def reset_form(e):
            selected_media_paths.clear()
            media_row.controls.clear()
            temp_input.value = ""
            inspector_comment.value = ""
            ai_response_text.value = "*Очікування медіафайлів...*"
            risk_indicator.bgcolor = ft.colors.GREY
            risk_indicator.content.value = "ОЦІНКА МАГАЗИНУ: НЕ ПРОВЕДЕНО"
            page.update()

        content_audit = ft.Column([
            title_row,
            ft.Row([
                ft.ElevatedButton("📷 ФОТО/ВІДЕО", on_click=trigger_media_picker, expand=True),
                ft.ElevatedButton("🔄 НОВИЙ", on_click=reset_form, color=ft.colors.RED_700),
            ]),
            media_row,
            ft.Row([object_dropdown, temp_input]),
            ft.Row([inspector_comment, ft.TextButton("🎤", on_click=lambda e: inspector_comment.focus())]),
            ft.ElevatedButton("🔍 ПРОВЕСТИ АУДИТ", on_click=perform_analysis, bgcolor=ft.colors.RED_900, color=ft.colors.WHITE),
            risk_indicator,
            ft.Divider(),
            ai_response_text,
            ft.Divider(),
            ft.ElevatedButton("📄 ЗБЕРЕГТИ АКТ ПЕРЕВІРКИ", on_click=generate_act, bgcolor=ft.colors.GREEN_700, color=ft.colors.WHITE)
        ], visible=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

        # ==========================================
        # ВКЛАДКА 2: БАЗА ШІ ТА ОЧИЩЕННЯ ПАМ'ЯТІ
        # ==========================================
        dd_base_category = ft.Dropdown(label="Виберіть відділ для налаштування", options=get_category_options(), value=list(user_prompts.keys())[0])
        tf_base_prompt = ft.TextField(label="Інструкція для ШІ (що шукати на фото?)", multiline=True, min_lines=4, max_lines=10)
        
        def refresh_dropdowns():
            opts = get_category_options()
            object_dropdown.options = opts
            dd_base_category.options = opts
            page.update()

        def on_base_category_change(e):
            tf_base_prompt.value = user_prompts.get(dd_base_category.value, "")
            page.update()
            
        dd_base_category.on_change = on_base_category_change
        on_base_category_change(None)

        def save_base_rule(e):
            cat = dd_base_category.value
            if cat:
                user_prompts[cat] = tf_base_prompt.value
                save_prompts(user_prompts)
                show_snack(f"✅ Правила для '{cat}' оновлено!", "green")

        tf_new_category = ft.TextField(label="Назва нового відділу", expand=True)
        def add_new_category(e):
            new_cat = tf_new_category.value.strip()
            if new_cat and new_cat not in user_prompts:
                user_prompts[new_cat] = "Введіть інструкцію для ШІ..."
                save_prompts(user_prompts)
                tf_new_category.value = ""
                refresh_dropdowns()
                dd_base_category.value = new_cat
                on_base_category_change(None)
                show_snack(f"➕ Додано новий відділ: {new_cat}", "blue")

        def sync_prompts_from_txt(e):
            imported_count = 0
            if os.path.exists(IMPORT_DIR):
                for filename in os.listdir(IMPORT_DIR):
                    if filename.lower().endswith(".txt"):
                        cat_name = filename[:-4] 
                        filepath = os.path.join(IMPORT_DIR, filename)
                        try:
                            with open(filepath, "r", encoding="utf-8") as f:
                                content = f.read().strip()
                            if content:
                                user_prompts[cat_name] = content
                                imported_count += 1
                        except: pass
            
            if imported_count > 0:
                save_prompts(user_prompts)
                refresh_dropdowns()
                show_snack(f"✅ Успішно завантажено {imported_count} відділів з TXT!", "green")
            else:
                show_snack(f"ℹ️ Не знайдено .txt файлів у папці Download/Frozen_Prompts_Import", "blue")

        def execute_clear_archives(e):
            del_reports = 0
            if os.path.exists(REPORTS_DIR):
                for f in os.listdir(REPORTS_DIR):
                    if (f.startswith("Frozen_Audit_") or f.startswith("MultiCook_Audit_")) and f.lower().endswith(".html"):
                        try:
                            os.remove(os.path.join(REPORTS_DIR, f))
                            del_reports += 1
                        except: pass
            
            dlg_confirm_clear.open = False
            show_snack(f"🗑️ Очищено: {del_reports} звітів!", "green")
            page.update()

        dlg_confirm_clear = ft.AlertDialog(
            title=ft.Text("⚠️ Підтвердження"),
            content=ft.Text("Ви дійсно хочете видалити всі збережені HTML-звіти додатку з пам'яті телефону? Цю дію неможливо скасувати."),
            actions=[
                ft.TextButton("Скасувати", on_click=lambda e: (setattr(dlg_confirm_clear, 'open', False), page.update())),
                ft.ElevatedButton("ТОЧНО ВИДАЛИТИ", on_click=execute_clear_archives, bgcolor=ft.colors.RED, color=ft.colors.WHITE)
            ]
        )
        page.overlay.append(dlg_confirm_clear)

        def trigger_clear_archives(e):
            dlg_confirm_clear.open = True
            page.update()

        content_base = ft.Column([
            ft.Text("🧠 БАЗА СТАНДАРТІВ", size=20, weight=ft.FontWeight.BOLD, color=ft.colors.PURPLE),
            ft.Text("Навчіть ШІ специфічним вимогам для кожного відділу.", color=ft.colors.GREY_700),
            
            ft.Container(
                content=ft.Column([
                    ft.Text("Масовий імпорт з ПК:", weight="bold"),
                    ft.Text("1. Підключіть телефон до ПК.\n2. Скиньте .txt файли у папку Download/Frozen_Prompts_Import\n3. Натисніть кнопку нижче.", size=12),
                    ft.ElevatedButton("📥 СИНХРОНІЗУВАТИ З ПАПКИ (TXT)", on_click=sync_prompts_from_txt, bgcolor=ft.colors.ORANGE_700, color=ft.colors.WHITE)
                ]),
                bgcolor=ft.colors.ORANGE_50, padding=10, border_radius=8
            ),
            ft.Divider(),
            
            dd_base_category,
            tf_base_prompt,
            ft.ElevatedButton("💾 ЗБЕРЕГТИ ПРАВИЛО ВРУЧНУ", on_click=save_base_rule, bgcolor=ft.colors.BLUE, color=ft.colors.WHITE),
            ft.Divider(),
            ft.Text("Створити один відділ вручну:", weight="bold"),
            ft.Row([tf_new_category, ft.ElevatedButton("➕ СТВОРИТИ", on_click=add_new_category, bgcolor=ft.colors.GREEN, color=ft.colors.WHITE)]),
            
            ft.Divider(),
            ft.Text("Керування пам'яттю телефону:", weight="bold", color=ft.colors.RED_900),
            ft.ElevatedButton("🗑️ ВИДАЛИТИ АРХІВИ (Звіти)", on_click=trigger_clear_archives, bgcolor=ft.colors.RED_900, color=ft.colors.WHITE, width=350)
            
        ], visible=False, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

        # ==========================================
        # НАВІГАЦІЯ (ВКЛАДКИ)
        # ==========================================
        def change_tab(tab_name):
            content_audit.visible = (tab_name == "audit")
            content_base.visible = (tab_name == "base")
            page.update()

        tabs_row = ft.Row([
            ft.TextButton("📝 АУДИТ ВІТРИН", on_click=lambda e: change_tab("audit"), expand=True),
            ft.TextButton("🧠 БАЗА ШІ", on_click=lambda e: change_tab("base"), expand=True)
        ], alignment=ft.MainAxisAlignment.SPACE_EVENLY)

        page.add(tabs_row, ft.Divider(), content_audit, content_base)
        
    except Exception as e:
        page.clean()
        page.scroll = ft.ScrollMode.ADAPTIVE
        page.add(
            ft.Text("❌ КРИТИЧНА ПОМИЛКА:", color="red", size=22, weight="bold"),
            ft.Text(traceback.format_exc(), selectable=True, size=12)
        )
        page.update()

ft.app(target=main)
