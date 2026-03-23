document.addEventListener('DOMContentLoaded', () => {
    // State
    let selectedImpact = null;
    let attachedFilesText = "";
    let attachedImagesBase64 = []; // Stores DataURL strings for Gemini Vision

    // DOM Elements
    const impactPills = document.querySelectorAll('.impact-pill');
    const dropZone = document.getElementById('dropZone');
    const fileUpload = document.getElementById('fileUpload');
    const fileList = document.getElementById('fileList');
    const logsInput = document.getElementById('logsInput');
    
    const timeRange = document.getElementById('timeRange');
    const affectedServices = document.getElementById('affectedServices');
    const keyStakeholders = document.getElementById('keyStakeholders');
    
    const generateBtn = document.getElementById('generateBtn');
    const btnText = document.getElementById('btnText');
    const errorBox = document.getElementById('errorBox');
    const successBox = document.getElementById('successBox');

    // Impact selection
    impactPills.forEach(pill => {
        pill.addEventListener('click', () => {
            impactPills.forEach(p => p.classList.remove('selected'));
            pill.classList.add('selected');
            selectedImpact = pill.dataset.impact;
        });
    });

    // File Drag & Drop
    dropZone.addEventListener('click', () => fileUpload.click());
    
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            handleFiles(e.dataTransfer.files);
        }
    });

    fileUpload.addEventListener('change', (e) => {
        if (e.target.files.length) {
            handleFiles(e.target.files);
        }
    });

    function handleFiles(files) {
        Array.from(files).forEach(file => {
            const ext = file.name.split('.').pop().toLowerCase();
            
            // Add pill to UI
            const pill = document.createElement('div');
            pill.className = 'file-item';
            pill.textContent = file.name;
            fileList.appendChild(pill);

            if (file.type.startsWith('image/')) {
                // Handle Images (Base64)
                pill.textContent = file.name + " (Reading Image...)";
                const reader = new FileReader();
                reader.onload = (e) => {
                    attachedImagesBase64.push(e.target.result);
                    pill.textContent = file.name + " (Vision Ready)";
                    pill.style.background = "rgba(16, 185, 129, 0.2)"; 
                };
                reader.readAsDataURL(file);
            } else if (['txt', 'log', 'json', 'csv'].includes(ext)) {
                // Read text files
                pill.textContent = file.name + " (Reading Text...)";
                const reader = new FileReader();
                reader.onload = (e) => {
                    attachedFilesText += `\n\n--- FILE: ${file.name} ---\n${e.target.result}`;
                    pill.textContent = file.name + " (Text Ready)";
                    pill.style.background = "rgba(16, 185, 129, 0.2)"; 
                };
                reader.readAsText(file);
            } else {
                // Unsupported / Fallback
                setTimeout(() => {
                    pill.textContent += " (Unsupported Type)";
                    pill.style.background = "rgba(239, 68, 68, 0.2)"; // red error tint
                }, 500);
            }
        });
    }

    const slaHours = document.getElementById('slaHours');
    const customersInput = document.getElementById('customers');

    // API Call
    generateBtn.addEventListener('click', async () => {
        const logs = logsInput.value.trim() + attachedFilesText;
        if (!logs) {
            showError("Please provide some logs or attach a file.");
            return;
        }

        const payload = {
            logs: logs,
            transcription: "", 
            time_range: timeRange.value.trim() || null,
            affected_services: affectedServices.value.trim() || null,
            impact: selectedImpact,
            key_stakeholders: keyStakeholders.value.trim() || null,
            sla_hours: parseInt(slaHours.value, 10),
            customers: customersInput.value.trim() || null,
            images: attachedImagesBase64
        };

        try {
            setLoading(true);
            errorBox.style.display = "none";
            successBox.style.display = "none";

            // Step 1: Analyze
            const analyzeRes = await fetch('/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!analyzeRes.ok) {
                const errData = await analyzeRes.json();
                throw new Error(errData.detail || 'Failed to analyze logs.');
            }

            const reportJson = await analyzeRes.json();

            // Step 2: Export PDF
            const pdfRes = await fetch('/export-pdf', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    request: payload,
                    report: reportJson
                })
            });

            if (!pdfRes.ok) throw new Error('Failed to generate PDF.');

            // Download PDF blob
            const blob = await pdfRes.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = reportJson.metrics && reportJson.metrics.incident_title 
                ? `Executive_Report_${reportJson.metrics.incident_title.replace(/\s+/g, '_')}.pdf`
                : 'executive_report.pdf';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);

            successBox.style.display = "block";

        } catch (err) {
            showError(err.message);
        } finally {
            setLoading(false);
        }
    });

    const exampleBtn = document.getElementById('exampleBtn');
    if (exampleBtn) {
        exampleBtn.addEventListener('click', async () => {
            try {
                const res = await fetch('/static/example_logs.txt');
                if (!res.ok) throw new Error("Could not load example logs.");
                const text = await res.text();
                
                // Populate forms according to the example spec
                logsInput.value = text;
                slaHours.value = "2";
                customersInput.value = "Hawk Bank";
                
                // Select High Impact visually and functionally
                impactPills.forEach(p => p.classList.remove('selected'));
                const highPill = Array.from(impactPills).find(p => p.dataset.impact === "High");
                if (highPill) {
                    highPill.classList.add('selected');
                    selectedImpact = "High";
                }
            } catch (err) {
                showError("Erro: " + err.message);
            }
        });
    }

    function setLoading(isLoading) {
        generateBtn.disabled = isLoading;
        btnText.textContent = isLoading ? "Generating Report... (This may take a minute)" : "Generate Professional Incident Report";
    }

    function showError(msg) {
        errorBox.textContent = msg;
        errorBox.style.display = "block";
    }
});
