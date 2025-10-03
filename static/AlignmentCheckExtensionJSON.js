class AlignmentCheckExtensionJSON extends Autodesk.Viewing.Extension {
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
      this.button = new Autodesk.Viewing.UI.Button('alignment-check-tool-button-json');
      this.button.setToolTip('Deterministic Alignment Check');
      const icon = this.button.container.querySelector('.adsk-button-icon');
      if (icon) {
            icon.style.backgroundImage = `url(${'https://img.icons8.com/sf-regular/48/bot.png'})`; 
            icon.style.backgroundSize = `24px`; 
            icon.style.backgroundRepeat = `no-repeat`; 
            icon.style.backgroundPosition = `center`; 
        }
      this.button.onClick = (ev) => {
        let dbIds = this.viewer.getSelection();
        this.viewer.model.getBulkProperties(dbIds, {}, function (results) {
            //filter Curves
            let curvesProperties;
            if (selectedItem.split('.')[1].toLowerCase() === 'dwg') {
                curvesProperties = results[0].properties.filter(property => property.displayCategory!=null).filter(property => property.displayCategory.includes('Curve'));
            } 
            else if (selectedItem.split('.')[1].toLowerCase() === 'nwc') {
                curvesProperties = results[0].properties.filter(property => property.displayCategory!=null).filter(property => property.displayCategory == 'Civil3D' && property.displayName.includes('Curve'));
                curvesProperties.map(property => {
                    property.displayCategory = property.displayName.split(':')[0];
                    property.displayName = property.displayName.split(':')[1];
                });            
            }
            else {
                swal.fire({
                    title: 'Unsupported File Type',
                    text: 'Only DWG and NWC files are supported',
                    icon: 'error'
                });
                return;
            }
            //Empty alignmentCheckDataJSON
            alignmentCheckDataJSON = {};
            //group by property.displayCategory
            for (let property of curvesProperties) {
                if (!alignmentCheckDataJSON[property.displayCategory]) {
                    alignmentCheckDataJSON[property.displayCategory] = {
                        checked: false,
                        result:''
                    };
                }
                alignmentCheckDataJSON[property.displayCategory][property.displayName] = property.displayValue;
            }
            swal.fire({
                title: 'Perform Alignment Check?',
                html: `
                    <div style="display: flex; flex-direction: column; align-items: center;">
                        <div style="margin-bottom: 1em;">
                            <label for="maxSpeedSlider"><b>Maximum Speed (mph):</b> <span id="maxSpeedValue">50</span></label><br>
                            <input type="range" id="maxSpeedSlider" min="10" max="120" value="50" step="1" style="width: 300px;" oninput="document.getElementById('maxSpeedValue').textContent = this.value;">
                        </div>
                        <table style="margin: 0 auto;">
                            ${Object.entries(alignmentCheckDataJSON).map(([key, value]) => `<tr><td>${key}</td><td>${value.result}</td></tr>`).join('')}
                        </table>
                    </div>
                `,
                icon: 'info',
                showCancelButton: true,
                confirmButtonText: 'Yes'
            }).then(async (result) => {
                if (result.isConfirmed) {
                    // Retrieve the selected speed from the slider
                    const maxSpeedSlider = document.getElementById('maxSpeedSlider');
                    const selectedSpeed = maxSpeedSlider ? maxSpeedSlider.value : 50;

                    // Check if jsonInput is loaded
                    if (!jsonInput) {
                        swal.fire({
                            title: 'Error',
                            text: 'Design standards not loaded. Please load a standards JSON file first.',
                            icon: 'error'
                        });
                        return;
                    }

                    // Get minimum radius standards based on selected speed
                    const minRadiusStandards = jsonInput.design_criteria.horizontal_curve.minimum_radius_by_speed;
                    
                    // Find the closest standard speed
                    const availableSpeeds = Object.keys(minRadiusStandards)
                        .map(k => parseInt(k.replace('_mph', '')))
                        .filter(n => !isNaN(n));
                    const selectedSpeedNum = parseInt(selectedSpeed);
                    const standardSpeed = availableSpeeds.reduce((prev, curr) => {
                        return Math.abs(curr - selectedSpeedNum) < Math.abs(prev - selectedSpeedNum) ? curr : prev;
                    });
                    
                    // Get minimum radius for the selected speed (using emax 4%)
                    const minRadius = minRadiusStandards[`${standardSpeed}_mph`]?.emax_4_percent_ft;
                    
                    // Check each curve
                    let resultsText = '';
                    let allPassed = true;
                    
                    Object.keys(alignmentCheckDataJSON).forEach(key => {
                        // Find the property that contains 'radius' (case insensitive)
                        let radiusPropName = Object.keys(alignmentCheckDataJSON[key]).find(propName => 
                            propName.toLowerCase().includes('radius')
                        );
                        
                        if (radiusPropName) {
                            let curveRadiusValue = alignmentCheckDataJSON[key][radiusPropName];
                            let radiusNum = parseFloat(curveRadiusValue);
                            
                            if (!isNaN(radiusNum) && minRadius) {
                                let curvePassed = radiusNum >= minRadius;
                                allPassed = allPassed && curvePassed;
                                alignmentCheckDataJSON[key].checked = true;
                                
                                if (curvePassed) {
                                    alignmentCheckDataJSON[key].result = '✓ PASS';
                                    resultsText += `${key}:\n`;
                                    resultsText += `  Radius: ${curveRadiusValue} ft\n`;
                                    resultsText += `  Status: PASS (Minimum required: ${minRadius} ft at ${standardSpeed} mph)\n\n`;
                                } else {
                                    alignmentCheckDataJSON[key].result = '✗ FAIL';
                                    resultsText += `${key}:\n`;
                                    resultsText += `  Radius: ${curveRadiusValue} ft\n`;
                                    resultsText += `  Status: FAIL (Minimum required: ${minRadius} ft at ${standardSpeed} mph)\n`;
                                    resultsText += `  Deficiency: ${(minRadius - radiusNum).toFixed(2)} ft below minimum\n\n`;
                                }
                            } else {
                                alignmentCheckDataJSON[key].result = '⚠ No Data';
                                resultsText += `${key}: Unable to validate (invalid radius or speed)\n\n`;
                            }
                        } else {
                            alignmentCheckDataJSON[key].result = '⚠ No Radius';
                            resultsText += `${key}: No radius property found\n\n`;
                        }
                    });
                    
                    // Add summary header
                    const summaryHeader = `${jsonInput.standard || 'Highway Design Standards'}\n` +
                        `Horizontal Curve Radius Check\n` +
                        `Design Speed: ${selectedSpeed} mph (Using ${standardSpeed} mph standard)\n` +
                        `Minimum Radius Required: ${minRadius} ft (emax=4%)\n` +
                        `Overall Result: ${allPassed ? 'PASS ✓' : 'FAIL ✗'}\n\n` +
                        `━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n` +
                        resultsText;
                    
                    //show the data back to the user formatted using swal
                    swal.fire({
                        title: 'Alignment Check Result',
                        html: `
                            <div>
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
                                <textarea id="alignmentCheckResult" style="width:100%;height:200px;font-family:monospace;font-size:12px;">${summaryHeader}</textarea>
                            </div>
                        `,
                        icon: allPassed ? 'success' : 'error',
                        confirmButtonText: 'Create Issue',
                        showCancelButton: true,
                    }).then(async (result) => {
                        if (result.isConfirmed) {
                            //create the issue
                            const issue = await fetch('/api/hubs/projects/' + selectedProjectId + '/issues', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({ 
                                    title: 'Alignment Check Result - ' + (allPassed ? 'PASS' : 'FAIL'), 
                                    description: summaryHeader, 
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
                }
            });
        });
      };
      this.button.addClass('alignment-check-json');
  
      this.group = new Autodesk.Viewing.UI.ControlGroup('alignment-check-tool-group-json');
      this.group.addControl(this.button);
      toolbar.addControl(this.group);
    }
  }
  
  Autodesk.Viewing.theExtensionManager.registerExtension('AlignmentCheckExtensionJSON', AlignmentCheckExtensionJSON);