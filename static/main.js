import { initViewer, loadModel } from './viewer.js';
import { initTree } from './sidebar.js';

const signin = document.getElementById('signin');
try {
    const help = document.getElementById('help');
    help.onclick = showHelpDialog;
    const resp = await fetch('/api/auth/profile');
    if (resp.ok) {
        const user = await resp.json();
        signin.innerText = `Logout (${user.name})`;
        signin.onclick = () => {
            window.location.href = 'https://developer.api.autodesk.com/authentication/v2/logout'
                + '?post_logout_redirect_uri=' + encodeURIComponent(window.location.origin);
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

        // Populate the skill selection dropdown
        const skillSelect = document.getElementById('skillSelect');
        try {
            const skillsResp = await fetch('/api/openai/skill/list');
            if (skillsResp.ok) {
                const skills = await skillsResp.json();
                skills.forEach(skill => {
                    const option = document.createElement('option');
                    option.value = skill.skill_id;
                    option.innerText = skill.name;
                    skillSelect.appendChild(option);
                });
            }
        } catch (e) {
            console.warn('Skills API unavailable — fallback mode only', e);
        }

        // Upload a skill ZIP
        const uploadSkillButton = document.getElementById('uploadSkill');
        uploadSkillButton.onclick = async () => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = '.zip,application/zip';
            input.onchange = async (event) => {
                const file = event.target.files[0];
                if (file) {
                    const formData = new FormData();
                    formData.append('file', file);
                    const resp = await fetch('/api/openai/skill/upload', {
                        method: 'POST',
                        body: formData
                    });
                    if (resp.ok) {
                        const data = await resp.json();
                        const option = document.createElement('option');
                        option.value = data.skill.skill_id;
                        option.innerText = data.skill.name;
                        skillSelect.appendChild(option);
                        skillSelect.value = data.skill.skill_id;
                        alert(`Skill "${data.skill.name}" uploaded successfully`);
                    } else {
                        const err = await resp.json();
                        alert('Failed to upload skill: ' + (err.error || 'Unknown error'));
                    }
                }
            };
            input.click();
        };

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
        signin.innerText = 'Sign In';
        signin.onclick = () => window.location.replace('/api/auth/login');
    }
    signin.style.visibility = 'visible';
} catch (err) {
    alert('Could not initialize the application. See console for more details.');
    console.error(err);
}

async function showHelpDialog() {
    Swal.fire({
        title: '<strong>Helpers</strong>',
        html:
        `
            <ul style='list-style-type:none; font-size:medium'>
                <li>
                    <a target='_blank' href='//tutorials.autodesk.io/#provision-access-in-other-products'>Provision</a>
                    the client id:
                    <input type='text' style='font-weight:bold' value='PVQ8rNNKB7ynJArbxhm6G8irUI4FbGgGtiCUb7QbGuX2c0AX' disabled>
                    </input>
                    in your hub.
                </li>
                <li>
                    Find the complete Source Code
                    <a target='_blank' href='https://github.com/autodesk-platform-services/aps-road-alignment-check-ai'>HERE</a>
                </li>
                <li>
                    You can find a sample JSON to use in this sample
                    <a href='https://github.com/autodesk-platform-services/aps-road-alignment-check-ai/assets/Highway-Design-Standards.json'>HERE</a>
                </li>
            </ul>
        `,
        showCloseButton: true,
        showCancelButton: false,
        focusConfirm: false,
        width: 600,
        confirmButtonText:
        '<i class="fa fa-thumbs-up"></i> OK',
    })
}
