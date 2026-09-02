// document is a builtin javascript object for working with html doc currently loaded in browser
document
    .getElementById("patient-form") //find by htmlid
    /*
    .addEventListener creates water for submit event on html doc
    then we use => to define a function
    */
    .addEventListener("submit", async (event) => { 
        event.preventDefault(); //tells browser to not refresh page when form submitted

        const body = { //getElementById get element objects representing element of id we passed
            //we make sure to convert strings to numbers as needed
            synthea_path: document.getElementById("synthea-path").value,
            count: Number(document.getElementById("count").value),
            state: document.getElementById("state").value,
            city: document.getElementById("city").value || null,
            min_age: Number(document.getElementById("min-age").value) || null,
            max_age: Number(document.getElementById("max-age").value) || null,
            condition: document.getElementById("condition").value || null,
        };

        //fetch is a browser api for making HTTP requests, we send one to our generate route here
        const response = await fetch("/generate", {
            method: "POST",
            //http requests contain headers, this header is telling FastAPI that we are sending a JSON
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(body) //convert javascript object to JSON
        });

        const result = await response.json(); //convert response to JSON

            //the response.ok ? is essentially saying 'if response.ok: patients generated else: stringify result'
        document.getElementById("result").textContent =
            response.ok ? "Patients generated!" : JSON.stringify(result);
    });