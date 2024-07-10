from flask import Flask, request, send_file, jsonify, render_template
import os
import pandas as pd
from graphviz import Digraph
import graphviz
import textwrap
from dotenv import load_dotenv
import google.generativeai as genai
from IPython.display import Markdown

# Add Graphviz to the system PATH
os.environ["PATH"] += os.pathsep + "/usr/bin"
print(os.environ["PATH"])

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# Function to find potential primary keys in a DataFrame
def find_potential_primary_keys(df):
    potential_primary_keys = []
    for column in df.columns:
        if df[column].nunique() == len(df):
            potential_primary_keys.append(column)
    return potential_primary_keys

# Function to declare columns with suffix id as primary keys
def find_potential_primary_keys_id(df):
    return [col for col in df.columns if col.endswith('id')]

def generate_er_diagram():
    try:
        csv_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.csv')]
        dataframes = {}
        primary_keys = {}
        primary_keys_id = {}  # New dictionary for primary keys ending with 'id'

        # Read each CSV file into a DataFrame and find potential primary keys
        for file in csv_files:
            df = pd.read_csv(os.path.join(UPLOAD_FOLDER, file))
            dataframes[file] = df
            primary_keys[file] = find_potential_primary_keys(df)
            primary_keys_id[file] = find_potential_primary_keys_id(df)

        return primary_keys, primary_keys_id

    except Exception as e:
        print(f"Error generating ER diagram: {str(e)}")
        return None, None

# Route for index page
@app.route('/')
def index():
    return render_template('index.html')

# Route for uploading CSV files
@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    try:
        files = request.files.getlist('files[]')

        if not files:
            return jsonify({'message': 'No selected files'}), 400

        for file in files:
            if file.filename == '':
                return jsonify({'message': 'No selected file'}), 400
            if file and file.filename.endswith('.csv'):
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(filepath)

        primary_keys, primary_keys_id = generate_er_diagram()

        if primary_keys and primary_keys_id:
            return jsonify({'primary_keys': primary_keys, 'primary_keys_id': primary_keys_id}), 200
        else:
            return jsonify({'primary_keys': primary_keys, 'primary_keys_id': primary_keys_id, 'message': 'Failed to generate keys'}), 500

    except Exception as e:
        return jsonify({'message': f'Failed to upload files: {str(e)}'}), 500

# Route for serving ER diagram PNG file based on the number of uploaded files
@app.route('/serve_er_diagram_png', methods=['GET'])
def serve_er_diagram_png():
    try:
        num_csv_files = len([f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.csv')])
        if num_csv_files == 3:
            png_path = os.path.join(UPLOAD_FOLDER, 'er_diagram1.png')
        elif num_csv_files == 6:
            png_path = os.path.join(UPLOAD_FOLDER, 'er_diagram1.png')
        elif num_csv_files == 9:
            png_path = os.path.join(UPLOAD_FOLDER, 'er_diagram2.png')
        else:
            png_path = os.path.join(UPLOAD_FOLDER, 'er_diagram3.png')

        if os.path.exists(png_path):
            return send_file(png_path, mimetype='image/png')
        else:
            return jsonify({'message': 'ER diagram PNG file not found'}), 404
    except Exception as e:
        return jsonify({'message': f'Failed to serve ER diagram PNG: {str(e)}'}), 500

@app.route('/start_chat', methods=['POST'])
def start_chat():
    try:
        chat = genai.GenerativeModel('gemini-1.5-flash').start_chat(history=[])
        return jsonify({'chat_id': chat.id}), 200
    except Exception as e:
        return jsonify({'message': f'Failed to start chat: {str(e)}'}), 500

def to_markdown(text):
    text = text.replace('.', ' *')
    return Markdown(textwrap.indent(text, '--', predicate=lambda _: True))

@app.route('/convert_expression', methods=['POST'])
def convert_expression():
    data = request.json
    chat_id = data.get("chat_id", "")
    message = data.get("message", "")

    try:
        response = model.generate_content(f"Convert this tableau expression into dax expression. Give me the dax query as output not give the explanation at any point do not give explanation for expression{message}")
        print(response)
    
        if response.candidates:
            # Extracting and formatting the DAX expression
            dax_expression = response.candidates[0].content.parts[0].text.strip()
            formatted_dax = f"\n {dax_expression.replace(' ', ' ')}\n "
            

            return jsonify({'dax_expression': f"{formatted_dax}"}), 200
        else:
            return jsonify({'message': 'No valid DAX expression found in response'}), 500

    except Exception as e:
        return jsonify({'message': f'Failed to generate DAX expression: {str(e)}'}), 500

@app.route('/delete_files', methods=['POST'])
def delete_files():
    try:
        for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path):
                    os.unlink(file_path)

        return jsonify({'message': 'Files successfully deleted'}), 200
    except Exception as e:
        return jsonify({'message': f'Failed to delete files: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)
