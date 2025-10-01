class AlignmentCheckExtension extends Autodesk.Viewing.Extension {
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
      this.button = new Autodesk.Viewing.UI.Button('alignment-check-tool-button');
      this.button.onClick = (ev) => {
        let dbIds = this.viewer.getSelection();
        this.viewer.model.getBulkProperties(dbIds, {}, function (results) {
            //filter Curves
            let curvesProperties = results[0].properties.filter(property => property.displayCategory!=null).filter(property => property.displayCategory.includes('Curve'));
            //group by property.displayCategory
            for (let property of curvesProperties) {
                if (!alignmentCheckData[property.displayCategory]) {
                    alignmentCheckData[property.displayCategory] = {
                        checked: false,
                        result:''
                    };
                }
                alignmentCheckData[property.displayCategory][property.displayName] = property.displayValue;
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
                            ${Object.entries(alignmentCheckData).map(([key, value]) => `<tr><td>${key}</td><td>${value.result}</td></tr>`).join('')}
                        </table>
                    </div>
                `,
                icon: 'info',
                showCancelButton: true,
                confirmButtonText: 'Yes'
            }).then(async (result) => {
                if (result.isConfirmed) {
                    //get the selected pdf
                    const pdfSelect = document.getElementById('pdfSelect');
                    const pdfValue = pdfSelect.value;
                    const vectorStoreId = pdfValue
                    // Retrieve the selected speed from the slider
                    const maxSpeedSlider = document.getElementById('maxSpeedSlider');
                    const selectedSpeed = maxSpeedSlider ? maxSpeedSlider.value : 50;

                    //aggregate the alignmentCheckData as string
                    let curves = '';
                    Object.keys(alignmentCheckData).forEach(key => {
                        curves += key;
                        if (!alignmentCheckData[key].checked) {
                            Object.keys(alignmentCheckData[key]).forEach(key2 => {
                                curves += `${key2}: ${alignmentCheckData[key][key2]}\n`;
                            });
                            curves += `Max Speed: ${selectedSpeed} mph\n`;
                            curves += '\n';
                        }
                        
                    });
                    //send request to /api/openai/query
                    const resp = await fetch('/api/openai/query', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            question: 'Check the curves against the road design standards: ' + curves,
                            vector_store_id: vectorStoreId
                        })
                    });
                    if (resp.ok) {
                        const data = await resp.json();
                        //show the data back to the user formatted using swal
                        swal.fire({
                            title: 'Alignment Check Result',
                            html: data.answer,
                            icon: 'info'
                        });
                        console.log(data);
                    } else {
                        alert('Failed to start check');
                    }
                }
            });
        });
      };
      this.button.addClass('alignment-check');
  
      this.group = new Autodesk.Viewing.UI.ControlGroup('alignment-check-tool-group');
      this.group.addControl(this.button);
      toolbar.addControl(this.group);
    }
  }
  
  Autodesk.Viewing.theExtensionManager.registerExtension('AlignmentCheckExtension', AlignmentCheckExtension);