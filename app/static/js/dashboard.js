const REFRESH_MS = 10000;

async function refreshDashboard() {

    try {

        const [signalsRes, systemRes] = await Promise.all([
            fetch("/api/signals/live"),
            fetch("/api/system/signal-engine")
        ]);

        const signals = await signalsRes.json();
        const system = await systemRes.json();

        updateMetrics(signals);
        updateSystem(system);

    } catch (e) {

        console.error(e);

    }

}

function updateMetrics(data){

    const metric=document.querySelector(".metric-value:last-of-type");

    if(metric){

        metric.innerText=data.signals_found;

    }

}

function updateSystem(data){

    const dots=document.querySelectorAll(".live-dot");

    dots.forEach(dot=>{

        dot.style.background="#00d084";

    });

}

setInterval(refreshDashboard,REFRESH_MS);

refreshDashboard();