// --- Handle the Generation Form ---
const DEFAULT_BACKEND_URL = "https://registration-depot-doc-jpeg.trycloudflare.com/";
const BACKEND_URL_STORAGE_KEY = "question_gui_backend_url";

function normalizeBackendUrl(url) {
    const trimmed = (url || "").trim();
    if (!trimmed) return DEFAULT_BACKEND_URL;

    let normalized = trimmed;
    if (!/^https?:\/\//i.test(normalized)) {
        normalized = `https://${normalized}`;
    }

    return normalized.endsWith("/") ? normalized : `${normalized}/`;
}

function getBackendUrl() {
    const input = document.getElementById('backend-url-input');
    const raw = input ? input.value : localStorage.getItem(BACKEND_URL_STORAGE_KEY);
    const normalized = normalizeBackendUrl(raw);
    localStorage.setItem(BACKEND_URL_STORAGE_KEY, normalized);
    if (input && input.value !== normalized) {
        input.value = normalized;
    }
    return normalized;
}

function initializeBackendUrlControls() {
    const backendInput = document.getElementById('backend-url-input');
    const resetBtn = document.getElementById('reset-backend-url-btn');
    if (!backendInput) return;

    const storedUrl = localStorage.getItem(BACKEND_URL_STORAGE_KEY);
    const initialUrl = normalizeBackendUrl(storedUrl || DEFAULT_BACKEND_URL);
    backendInput.value = initialUrl;
    localStorage.setItem(BACKEND_URL_STORAGE_KEY, initialUrl);

    const persist = () => {
        const normalized = normalizeBackendUrl(backendInput.value);
        backendInput.value = normalized;
        localStorage.setItem(BACKEND_URL_STORAGE_KEY, normalized);
    };

    backendInput.addEventListener('blur', persist);
    backendInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            persist();
        }
    });

    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            backendInput.value = DEFAULT_BACKEND_URL;
            localStorage.setItem(BACKEND_URL_STORAGE_KEY, DEFAULT_BACKEND_URL);
        });
    }
}

initializeBackendUrlControls();

document.getElementById('generate-form').addEventListener('submit', async (e) => {
    e.preventDefault(); // Stop the page from reloading

    const backendUrl = getBackendUrl();

    const form = e.target;
    const submitBtn = document.getElementById('generate-btn');
    const loadingIndicator = document.getElementById('loading-indicator');
    const terminal = document.getElementById('live-terminal'); // Grabbing the terminal box!
    const resultBox = document.getElementById('result-box');
    const errorBox = document.getElementById('error-box');
    const accessCodeDisplay = document.getElementById('access-code-display');

    // Hide old results and show the loading state
    resultBox.classList.add('hidden');
    errorBox.classList.add('hidden');
    loadingIndicator.classList.remove('hidden');
    submitBtn.disabled = true;

    if (terminal) {
        terminal.textContent = "Connecting to server...\n";
    }

    // Package up the file and the form inputs
    const formData = new FormData();
    formData.append('file', document.getElementById('pdf-file').files[0]);
    formData.append('fallback_mode', document.getElementById('fallback-mode').value);
    formData.append('num_mcq', document.getElementById('num-mcq').value);
    formData.append('num_tf', document.getElementById('num-tf').value);
    formData.append('num_short', document.getElementById('num-short').value);

    try {
        // 1. Send it to the FastAPI backend to start the background job
        const response = await fetch(`${backendUrl}api/generate-test`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        let finalData = data;
        if (response.ok && data.status === "duplicate_found") {
            const message = [
                "This PDF was already processed.",
                "Press OK to reuse the previous generated test instantly.",
                "Press Cancel to regenerate only the test from cached claims."
            ].join("\n");
            const reuse = window.confirm(message);

            const resolveFormData = new FormData();
            resolveFormData.append('duplicate_token', data.duplicate_token);
            resolveFormData.append('action', reuse ? 'reuse' : 'regenerate');

            const resolveResponse = await fetch(`${backendUrl}api/resolve-duplicate`, {
                method: 'POST',
                body: resolveFormData
            });
            finalData = await resolveResponse.json();

            if (!resolveResponse.ok || finalData.status !== "success") {
                throw new Error(finalData.message || 'Failed to resolve duplicate upload.');
            }
        }

        // 2. Check if the backend gave us the thumbs up that the job STARTED
        if (response.ok && finalData.status === "success") {
            const accessCode = finalData.access_code;
            
            // 3. Start polling the server for logs every 1 second (1000ms)
            const pollInterval = setInterval(async () => {
                try {
                    const logUrl = `${backendUrl}api/progress/${accessCode}?_=${Date.now()}`;
                    const logResponse = await fetch(logUrl, {
                        cache: 'no-store',
                        headers: {
                            'Cache-Control': 'no-cache, no-store, must-revalidate',
                            'Pragma': 'no-cache',
                            'Expires': '0'
                        }
                    });
                    const logData = await logResponse.json();
                    
                    if (terminal) {
                        // Update the text and auto-scroll to the bottom
                        terminal.textContent = logData.log;
                        terminal.scrollTop = terminal.scrollHeight;
                    }

                    // 4. Stop checking if the script says "ALL DONE!"
                    if (logData.log.includes("ALL DONE!")) {
                        clearInterval(pollInterval);
                        loadingIndicator.classList.add('hidden');

                        if (logData.log.includes("CRITICAL ERROR")) {
                            errorBox.textContent = "The pipeline crashed. Check the terminal logs above.";
                            errorBox.classList.remove('hidden');
                        } else {
                            accessCodeDisplay.textContent = accessCode;
                            resultBox.classList.remove('hidden');

                            // Wire action buttons for this specific run code.
                            document.getElementById('download-btn').onclick = () => {
                                window.open(`${backendUrl}api/get-test/${accessCode}`, '_blank');
                            };

                            document.getElementById('take-test-btn').onclick = () => {
                                window.location.href = `quiz.html?code=${accessCode}`;
                            };
                        }
                        submitBtn.disabled = false;
                    }
                } catch (pollError) {
                    console.error("Error fetching progress:", pollError);
                }
            }, 1000);

        } else {
            // If the server rejected the initial POST request
            throw new Error(finalData.message || 'The pipeline failed to start.');
            loadingIndicator.classList.add('hidden');
            submitBtn.disabled = false;
        }
    } catch (error) {
        // If the fetch request itself completely failed (e.g., server offline)
        errorBox.textContent = `Error: ${error.message}`;
        errorBox.classList.remove('hidden');
        loadingIndicator.classList.add('hidden');
        submitBtn.disabled = false;
    } 
});

// --- Handle the Retrieval Form ---
document.getElementById('retrieve-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const accessCode = document.getElementById('access-code-input').value.trim();
    const backendUrl = getBackendUrl();
    
    if (accessCode) {
        // Opening the URL in a new tab will show or download the JSON file
        window.open(`${backendUrl}api/get-test/${accessCode}`, '_blank');
    }
});

document.getElementById('retrieve-take-test-btn').addEventListener('click', () => {
    const accessCode = document.getElementById('access-code-input').value.trim();
    if (accessCode) {
        window.location.href = `quiz.html?code=${accessCode}`;
    }
});

document.getElementById('retrieve-view-log-btn').addEventListener('click', () => {
    const accessCode = document.getElementById('access-code-input').value.trim();
    const backendUrl = getBackendUrl();
    if (accessCode) {
        window.open(`${backendUrl}api/get-log/${accessCode}`, '_blank');
    }
});