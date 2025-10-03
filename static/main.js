import { initViewer, loadModel } from './viewer.js';
import { initTree } from './sidebar.js';

const login = document.getElementById('login');
try {
    const resp = await fetch('/api/auth/profile');
    if (resp.ok) {
        const user = await resp.json();
        login.innerText = `Logout (${user.name})`;
        login.onclick = () => {
            const iframe = document.createElement('iframe');
            iframe.style.visibility = 'hidden';
            iframe.src = 'https://accounts.autodesk.com/Authentication/LogOut';
            document.body.appendChild(iframe);
            iframe.onload = () => {
                window.location.replace('/api/auth/logout');
                document.body.removeChild(iframe);
            };
        }
        const viewer = await initViewer(document.getElementById('preview'));
        initTree('#tree', (id) => loadModel(viewer, window.btoa(id).replace(/=/g, '')));

        //load a json file to be used as base for Deterministic Alignment Check
        const jsonInputButton = document.getElementById('jsonInput');
        jsonInputButton.onclick = async () => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'application/json';
            input.onchange = async (event) => {
                const file = event.target.files[0];
                if (file) {
                    //send the file to the server
                    const formData = new FormData();
                    formData.append('file', file);
                    const resp = await fetch('/api/json/upload', {
                        method: 'POST',
                        body: formData
                    });
                    if (resp.ok) {
                        const data = await resp.json();
                        jsonInput = data.data;
                        console.log('Design standards loaded to jsonInput:', jsonInput);
                    } else {
                        alert('Failed to upload JSON file');
                    }
                }
            };
            input.click();
        };

        // Populate the PDF selection dropdown
        const pdfSelect = document.getElementById('pdfSelect');
        const indexedPDFs = await fetch('/api/openai/indexedpdfs');
        const pdfList = await indexedPDFs.json();
        pdfList.forEach(pdf => {
            const option = document.createElement('option');
            option.value = pdf.vector_store_id;
            option.innerText = pdf.filename;
            pdfSelect.appendChild(option);
        });

        //Index a PDF to be used as knowledge base for OpenAI
        const indexPDFButton = document.getElementById('indexpdf');
        indexPDFButton.onclick = async () => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'application/pdf';
            input.onchange = async (event) => {
                const file = event.target.files[0];
                if (file) {
                    const formData = new FormData();
                    formData.append('file', file);
                    const resp = await fetch('/api/openai/indexpdf', {
                        method: 'POST',
                        body: formData
                    });
                    if (resp.ok) {
                        alert('PDF indexed successfully');
                    } else {
                        alert('Failed to index PDF');
                    }
                }
            };
            input.click();
        };
    } else {
        login.innerText = 'Login';
        login.onclick = () => window.location.replace('/api/auth/login');
    }
    login.style.visibility = 'visible';
} catch (err) {
    alert('Could not initialize the application. See console for more details.');
    console.error(err);
}
