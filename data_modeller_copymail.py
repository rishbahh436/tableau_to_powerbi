from flask import Flask, request, send_file, jsonify, render_template
import os
import pandas as pd
from graphviz import Digraph
import graphviz

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Function to find potential primary keys in a DataFrame
def find_potential_primary_keys(df):
    potential_primary_keys = []
    for column in df.columns:
        if df[column].nunique() == len(df):
            potential_primary_keys.append(column)
    return potential_primary_keys

# Function to generate the ER diagram as .dot and .png files
def generate_er_diagram():
    try:
        csv_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.endswith('.csv')]
        dataframes = {}
        primary_keys = {}

        # Read each CSV file into a DataFrame and find potential primary keys
        for file in csv_files:
            df = pd.read_csv(os.path.join(UPLOAD_FOLDER, file))
            dataframes[file] = df
            primary_keys[file] = find_potential_primary_keys(df)

        # Create a Digraph object from graphviz
        dot = Digraph(comment='ER Diagram')

        # Add nodes (tables) and edges (relationships)
        for file in csv_files:
            label = f"{file}\n({', '.join(primary_keys[file])})"
            dot.node(file, label=label, shape='box')

        foreign_keys = {}
 
        # Find relationships (edges) between tables based on primary keys
        for file, keys in primary_keys.items():
            for key in keys:
                for other_file, other_df in dataframes.items():
                    if file != other_file and key in other_df.columns:
                        dot.edge(file, other_file)
                        foreign_keys[key] = []
                        foreign_keys[key].append(other_file)

        # Dictionary to store table types
        table_types = {}
        
        # Determine table types
        for file in csv_files:
            is_fact = False
            for key in primary_keys[file]:
                if key in foreign_keys:
                    is_fact = True
                    break
            if is_fact:
                table_types[file] = 'Fact'
            else:
                table_types[file] = 'Dimension'
        
        # Print table types
        for file, table_type in table_types.items():
            print(f"Table: {file}")
            print(f"Type: {table_type}")
            print("\n")
        
        # Create a graph to represent relationships using Graphviz
        dot = graphviz.Digraph(comment = 'ER Diagram')
        
        # Add nodes for each table
        for file in csv_files:
            label = f"{file}\n({table_types[file]})"
            dot.node(file, label = label, shape='box', style = 'filled', color = 'lightgray')
        
        # Add edges for primary key to foreign key relationships
        for key, tables in foreign_keys.items():
            for table in tables:
                for file in primary_keys:
                    if key in primary_keys[file]:
                        dot.edge(file, table, label = key)
        

        output_path = 'output/er_diagram'
        dot.render(output_path, view=False)
        # Specify paths for saving .dot and .png files
        dot_path = os.path.join(UPLOAD_FOLDER, 'er_diagram')
        png_path = os.path.join(UPLOAD_FOLDER, 'er_diagram')

        # Save the diagram as .dot file
        dot.save(dot_path)

        # Render the diagram as .png
        dot.render(png_path, format='png')

        return primary_keys, dot_path, png_path

    except Exception as e:
        # Log the exception for debugging
        print(f"Error generating ER diagram: {str(e)}")
        return None, str(e), None

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

        return jsonify({'message': 'Files successfully uploaded'}), 200
    except Exception as e:
        return jsonify({'message': f'Failed to upload files: {str(e)}'}), 500

# Route for generating ER diagram
@app.route('/generate_er_diagram_route', methods=['GET'])
def generate_er_diagram_route():
    try:
        primary_keys, dot_path, png_path = generate_er_diagram()
        if dot_path and png_path:
            return jsonify({'primary_keys': primary_keys, 'dot_path': dot_path, 'png_path': png_path})
        else:
            return jsonify({'message': 'Failed to generate ER diagram'}), 500
    except Exception as e:
        return jsonify({'message': f'Failed to generate ER diagram: {str(e)}'}), 500

# Route for downloading ER diagram .dot file
@app.route('/download_er_diagram_dot', methods=['GET'])
def download_er_diagram_dot():
    try:
        dot_path = os.path.join(app.config['UPLOAD_FOLDER'], 'er_diagram.dot')
        if os.path.exists(dot_path):
            return send_file(dot_path, as_attachment=True)
        else:
            return jsonify({'message': 'ER diagram .dot file not found'}), 404
    except Exception as e:
        return jsonify({'message': f'Failed to download ER diagram .dot file: {str(e)}'}), 500

# Route for serving ER diagram PNG file
@app.route('/serve_er_diagram_png', methods=['GET'])
def serve_er_diagram_png():
    try:
        png_path = os.path.join(app.config['UPLOAD_FOLDER'], 'er_diagram.png')
        if os.path.exists(png_path):
            return send_file(png_path, mimetype='image/png')
        else:
            return jsonify({'message': 'ER diagram PNG file not found'}), 404
    except Exception as e:
        return jsonify({'message': f'Failed to serve ER diagram PNG: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True)