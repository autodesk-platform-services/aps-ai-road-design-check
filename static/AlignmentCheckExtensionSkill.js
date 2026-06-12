class AlignmentCheckExtensionSkill extends Autodesk.Viewing.Extension {
    constructor(viewer, options) {
        super(viewer, options);
    }

    load() {
        return true;
    }

    unload() {
        return true;
    }

    onToolbarCreated(toolbar) {
        this.button = new Autodesk.Viewing.UI.Button('alignment-check-tool-button-skill');
        this.button.setToolTip('OpenAI Skills Alignment Check');
        const icon = this.button.container.querySelector('.adsk-button-icon');
        if (icon) {
            icon.style.backgroundImage = `url(${'https://img.icons8.com/sf-regular/48/learning.png'})`;
            icon.style.backgroundSize = `24px`;
            icon.style.backgroundRepeat = `no-repeat`;
            icon.style.backgroundPosition = `center`;
        }

        this.button.onClick = (ev) => {
            let dbIds = this.viewer.getSelection();
            this.viewer.model.getBulkProperties(dbIds, {}, function (results) {
                let curvesProperties;
                if (selectedItem.split('.')[1].toLowerCase() === 'dwg') {
                    curvesProperties = results[0].properties
                        .filter(p => p.displayCategory != null)
                        .filter(p => p.displayCategory.includes('Curve'));
                } else if (selectedItem.split('.')[1].toLowerCase() === 'nwc') {
                    curvesProperties = results[0].properties
                        .filter(p => p.displayCategory != null)
                        .filter(p => p.displayCategory === 'Civil3D' && p.displayName.includes('Curve'));
                    curvesProperties.map(p => {
                        p.displayCategory = p.displayName.split(':')[0];
                        p.displayName = p.displayName.split(':')[1];
                    });
                } else {
                    swal.fire({
                        title: 'Unsupported File Type',
                        text: 'Only DWG and NWC files are supported',
                        icon: 'error'
                    });
                    return;
                }

                alignmentCheckDataSkill = {};
                for (let property of curvesProperties) {
                    if (!alignmentCheckDataSkill[property.displayCategory]) {
                        alignmentCheckDataSkill[property.displayCategory] = { checked: false, result: '' };
                    }
                    alignmentCheckDataSkill[property.displayCategory][property.displayName] = property.displayValue;
                }

                swal.fire({
                    title: 'Perform Skills Alignment Check?',
                    html: `
                        <div style="display:flex;flex-direction:column;align-items:center;">
                            <div style="margin-bottom:1em;">
                                <label for="maxSpeedSliderSkill"><b>Maximum Speed (mph):</b> <span id="maxSpeedValueSkill">50</span></label><br>
                                <input type="range" id="maxSpeedSliderSkill" min="10" max="120" value="50" step="1"
                                    style="width:300px;"
                                    oninput="document.getElementById('maxSpeedValueSkill').textContent = this.value;">
                            </div>
                            <table style="margin:0 auto;">
                                ${Object.entries(alignmentCheckDataSkill)
                                    .map(([key, value]) => `<tr><td>${key}</td><td>${value.result}</td></tr>`)
                                    .join('')}
                            </table>
                        </div>
                    `,
                    icon: 'info',
                    showCancelButton: true,
                    confirmButtonText: 'Run Check',
                    showLoaderOnConfirm: true,
                    preConfirm: async () => {
                        const pdfSelect = document.getElementById('pdfSelect');
                        const vectorStoreId = pdfSelect ? pdfSelect.value : null;
                        const maxSpeedSlider = document.getElementById('maxSpeedSliderSkill');
                        const selectedSpeed = maxSpeedSlider ? maxSpeedSlider.value : 50;
                        const units = viewer.model.getUnitString();

                        // Build the human-readable question for retrieval
                        let curveSummary = '';
                        const designData = {};
                        Object.keys(alignmentCheckDataSkill).forEach(curveKey => {
                            const curveProps = alignmentCheckDataSkill[curveKey];
                            designData[curveKey] = {};
                            curveSummary += curveKey + '\n';
                            Object.keys(curveProps).forEach(propName => {
                                if (propName !== 'checked' && propName !== 'result') {
                                    curveSummary += `  ${propName}: ${curveProps[propName]} ${units}\n`;
                                    designData[curveKey][propName] = curveProps[propName];
                                }
                            });
                            curveSummary += `  Max Speed: ${selectedSpeed} mph\n\n`;
                            designData[curveKey]['Max Speed (mph)'] = selectedSpeed;
                        });

                        const resp = await fetch('/api/openai/skill/query', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                question: `Check the curves against road design standards (units ${units}):\n${curveSummary}`,
                                design_data: designData,
                                vector_store_id: vectorStoreId
                            })
                        });
                        return resp.json();
                    }
                }).then(async (resp) => {
                    if (!resp.value || !resp.value.success) {
                        swal.fire({
                            title: 'Check Failed',
                            text: resp.value ? resp.value.error : 'Unknown error',
                            icon: 'error'
                        });
                        return;
                    }

                    const report = resp.value.report;
                    const overallStatus = resp.value.overall_status;
                    const skillUsed = resp.value.skill_used;

                    // Build the result table from the structured JSON report
                    let reportHtml = '';
                    if (report.parse_error) {
                        // Fallback: show raw text if JSON parsing failed
                        reportHtml = `<pre style="text-align:left;font-size:11px;">${report.raw || ''}</pre>`;
                    } else {
                        const statusColor = overallStatus === 'pass' ? '#27ae60'
                            : overallStatus === 'fail' ? '#e74c3c' : '#f39c12';

                        reportHtml += `
                            <div style="margin-bottom:10px;">
                                <b>Status:</b>
                                <span style="color:${statusColor};font-weight:bold;text-transform:uppercase;">
                                    ${overallStatus}
                                </span>
                                &nbsp;&nbsp;<small style="color:#888;">skill: ${skillUsed}</small>
                            </div>`;

                        if (report.summary) {
                            reportHtml += `<p style="margin-bottom:10px;font-style:italic;">${report.summary}</p>`;
                        }

                        if (report.checks && report.checks.length > 0) {
                            reportHtml += `
                                <table style="width:100%;font-size:11px;border-collapse:collapse;margin-bottom:10px;">
                                    <thead>
                                        <tr style="background:#f0f0f0;">
                                            <th style="padding:4px;border:1px solid #ddd;text-align:left;">Check</th>
                                            <th style="padding:4px;border:1px solid #ddd;">Value</th>
                                            <th style="padding:4px;border:1px solid #ddd;">Status</th>
                                            <th style="padding:4px;border:1px solid #ddd;">Conf.</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${report.checks.map(check => {
                                            const sc = check.status === 'pass' ? '#27ae60'
                                                : check.status === 'fail' ? '#e74c3c' : '#f39c12';
                                            return `
                                                <tr>
                                                    <td style="padding:4px;border:1px solid #ddd;text-align:left;">
                                                        <b>${check.design_field || check.requirement_id || ''}</b>
                                                        ${check.standard_section ? `<br><small>${check.standard_section}</small>` : ''}
                                                        ${check.remediation ? `<br><small style="color:#e74c3c;">↳ ${check.remediation}</small>` : ''}
                                                    </td>
                                                    <td style="padding:4px;border:1px solid #ddd;text-align:center;">
                                                        ${check.design_value != null ? check.design_value : '—'}
                                                    </td>
                                                    <td style="padding:4px;border:1px solid #ddd;text-align:center;color:${sc};font-weight:bold;">
                                                        ${(check.status || '').toUpperCase()}
                                                    </td>
                                                    <td style="padding:4px;border:1px solid #ddd;text-align:center;">
                                                        ${check.confidence || '—'}
                                                    </td>
                                                </tr>`;
                                        }).join('')}
                                    </tbody>
                                </table>`;
                        }

                        if (report.missing_design_data && report.missing_design_data.length > 0) {
                            reportHtml += `<p style="color:#e67e22;font-size:11px;"><b>Missing data:</b> ${
                                report.missing_design_data.map(m => m.field).join(', ')
                            }</p>`;
                        }
                    }

                    swal.fire({
                        title: 'Skills Alignment Check Result',
                        html: `
                            <div>
                                <input type="text" id="issueTitle" style="width:100%;margin-bottom:10px;" placeholder="Issue Title">
                                <label for="issueSubtypeSelect"><b>Issue Subtype:</b></label>
                                <select id="issueSubtypeSelect" style="width:100%;margin-bottom:10px;">
                                    ${
                                        Object.keys(issueSubTypes).length > 0
                                        ? Object.entries(issueSubTypes).map(([name, id]) =>
                                            `<option value="${id}">${name}</option>`
                                          ).join('')
                                        : '<option value="">No subtypes found</option>'
                                    }
                                </select>
                                <div style="border:1px solid #ddd;border-radius:4px;padding:10px;max-height:300px;overflow-y:auto;margin-bottom:10px;text-align:left;">
                                    ${reportHtml}
                                </div>
                                <textarea id="alignmentCheckResult" style="width:100%;height:100px;">${
                                    report.summary || JSON.stringify(report, null, 2)
                                }</textarea>
                            </div>
                        `,
                        icon: overallStatus === 'pass' ? 'success' : overallStatus === 'fail' ? 'error' : 'warning',
                        confirmButtonText: 'Create Issue',
                        showCancelButton: true,
                        width: 700
                    }).then(async (result) => {
                        if (result.isConfirmed) {
                            const issue = await fetch('/api/hubs/projects/' + selectedProjectId + '/issues', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    title: document.getElementById('issueTitle').value,
                                    description: document.getElementById('alignmentCheckResult').value,
                                    status: 'open',
                                    issue_subtype_id: document.getElementById('issueSubtypeSelect').value
                                })
                            });
                            if (issue.ok) {
                                alert('Issue created successfully');
                            } else {
                                alert('Failed to create issue');
                            }
                        }
                    });
                });
            });
        };

        this.button.addClass('alignment-check-skill');
        this.group = new Autodesk.Viewing.UI.ControlGroup('alignment-check-tool-group-skill');
        this.group.addControl(this.button);
        toolbar.addControl(this.group);
    }
}

Autodesk.Viewing.theExtensionManager.registerExtension('AlignmentCheckExtensionSkill', AlignmentCheckExtensionSkill);
