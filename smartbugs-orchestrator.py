from flask import Flask, request, jsonify
import subprocess
import os
import json

app = Flask(__name__)

def check_docker():
    try:
        result = subprocess.run(['docker', 'info'], capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(result.stderr)
        return True, result.stdout
    except Exception as e:
        return False, str(e)

@app.route('/audit/contract', methods=['GET'])
def execute_smartbugs():
    docker_running, docker_info = check_docker()
    if not docker_running:
        return jsonify({'error': 'Docker no está corriendo o no es accesible', 'details': docker_info}), 500

    # Obtener el texto del cuerpo de la solicitud
    data = request.get_json()
    if not data or 'contractCode' not in data:
        return jsonify({'error': 'No se proporcionó el campo "contractCode"'}), 400

    contract_code = data['contractCode']

    # Ruta al directorio de SmartBugs
    smartbugs_path = os.path.join(os.getcwd())
    if not os.path.exists(smartbugs_path):
        return jsonify({'error': f'El directorio {smartbugs_path} no existe'}), 500

    # Crear el archivo test.hex con el contenido proporcionado
    test_file_path = os.path.join(smartbugs_path, 'test.hex')
    try:
        with open(test_file_path, 'w') as file:
            file.write(contract_code)
    except Exception as e:
        return jsonify({'error': f'Error al crear el archivo: {str(e)}'}), 500

    # Comando para ejecutar SmartBugs
    command = [
        'python3', '-m', 'sb', '-t', 'mythril', '--runtime',
        '--processes', '10', '--results', smartbugs_path+"/resultados", '--json', '-f', test_file_path
    ]

    try:
        print("Ejecutando SmartBugs...")
        process = subprocess.Popen(command, cwd=smartbugs_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Capturar toda la salida de stdout y stderr
        stdout, stderr = process.communicate()

        # Verificar el código de retorno
        if process.returncode != 0:
            print(f"ERROR: {stderr}")
            return jsonify({'error': 'Error al ejecutar SmartBugs', 'details': stderr}), 500

        # Leer el archivo JSON generado por SmartBugs
        output_file_path = os.path.join(smartbugs_path, 'resultados', 'results.json')  # Ajusta esto al nombre y ubicación correctos del archivo JSON
        if not os.path.exists(output_file_path):
            return jsonify({'error': 'No se encontró el archivo de resultados JSON'}), 500

        with open(output_file_path, 'r') as json_file:
            output_data = json.load(json_file)

        # Suponiendo que el archivo JSON tiene una estructura conocida, extraer los datos necesarios
        address = output_data.get('address', 'N/A')  # Reemplaza con la clave real si es diferente
        contract_analysis_txt = json.dumps(output_data)  # Convierte el JSON completo a texto para el análisis

        # Construir la respuesta con los dos campos específicos
        response = {
            'address': address,
            'contractAnalysisTxt': contract_analysis_txt
        }

        return jsonify(response), 200

    except Exception as e:
        return jsonify({'error': f'Error al ejecutar SmartBugs: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
