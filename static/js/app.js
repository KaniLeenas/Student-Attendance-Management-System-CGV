const SAMS = {
  colors: { ok: '#22c55e', bad: '#ef4444', ac: '#38bdf8',
            grid: '#1e293b', txt: '#94a3b8' },

  async overviewChart(id) {
    const el = document.getElementById(id);
    if (!el) return;
    const d = await (await fetch('/api/overview')).json();
    new Chart(el, {
      type: 'bar',
      data: {
        labels: d.labels,
        datasets: [{
          label: 'Attendance %', data: d.values, borderRadius: 6,
          backgroundColor: d.values.map(v => v >= 80 ? SAMS.colors.ok
                                                     : SAMS.colors.bad)
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { labels: { color: SAMS.colors.txt } } },
        scales: {
          y: { max: 100, ticks: { color: SAMS.colors.txt },
               grid: { color: SAMS.colors.grid } },
          x: { ticks: { color: SAMS.colors.txt }, grid: { display: false } }
        }
      }
    });
  },

  async studentCharts() {
    const t = document.getElementById('timeline');
    if (t) {
      const d = await (await fetch('/api/student/' + t.dataset.student)).json();
      new Chart(t, {
        type: 'bar',
        data: {
          labels: d.labels,
          datasets: [{
            label: 'Present (1) / Absent (0)', data: d.values, borderRadius: 6,
            backgroundColor: d.values.map(v => v ? SAMS.colors.ok
                                                 : SAMS.colors.bad)
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { labels: { color: SAMS.colors.txt } } },
          scales: {
            y: { max: 1, ticks: { stepSize: 1, color: SAMS.colors.txt },
                 grid: { color: SAMS.colors.grid } },
            x: { ticks: { color: SAMS.colors.txt }, grid: { display: false } }
          }
        }
      });
    }
    const n = document.getElementById('donut');
    if (n) {
      new Chart(n, {
        type: 'doughnut',
        data: {
          labels: ['Present', 'Absent'],
          datasets: [{
            data: [+n.dataset.present, +n.dataset.absent],
            backgroundColor: [SAMS.colors.ok, SAMS.colors.bad], borderWidth: 0
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false, cutout: '62%',
          plugins: { legend: { labels: { color: SAMS.colors.txt } } }
        }
      });
    }
  },

  dropzone() {
    const drop = document.getElementById('drop'),
          input = document.getElementById('sheet'),
          name = document.getElementById('fname');
    if (!drop) return;
    input.addEventListener('change', () => {
      if (input.files[0]) name.textContent = input.files[0].name;
    });
    ['dragenter', 'dragover'].forEach(e => drop.addEventListener(e, ev => {
      ev.preventDefault(); drop.classList.add('hot');
    }));
    ['dragleave', 'drop'].forEach(e => drop.addEventListener(e, ev => {
      ev.preventDefault(); drop.classList.remove('hot');
    }));
    drop.addEventListener('drop', ev => {
      input.files = ev.dataTransfer.files;
      if (input.files[0]) name.textContent = input.files[0].name;
    });
  },

  selects() {
    document.querySelectorAll('.sel').forEach(s =>
      s.addEventListener('change', () => {
        s.classList.toggle('absent', s.value === 'absent');
      }));
  }
};