document
    .getElementById("patient-form")
    .addEventListener("submit", async (event) => {
        event.preventDefault();

        const body = {
            synthea_path: document.getElementById("synthea-path").value,
            count: Number(document.getElementById("count").value),
            state: document.getElementById("state").value,
            city: document.getElementById("city").value || null,
            min_age: Number(document.getElementById("min-age").value) || null,
            max_age: Number(document.getElementById("max-age").value) || null,
            condition: document.getElementById("condition").value || null,
        };

        const response = await fetch("/generate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(body)
        });

        const result = await response.json();

        document.getElementById("result").textContent =
            response.ok ? "Patients generated!" : JSON.stringify(result);
    });