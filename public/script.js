
let transaksiData = [];

let jenisSaatIni = "pemasukan";

let cashflowChart = null;

let categoryChart = null;



// =====================================================
// FORMAT RUPIAH
// =====================================================

function formatRupiah(angka) {

    return new Intl.NumberFormat(
        "id-ID",
        {
            style: "currency",
            currency: "IDR",
            maximumFractionDigits: 0
        }
    ).format(angka || 0);

}



// =====================================================
// TANGGAL HARI INI
// =====================================================

function tanggalHariIni() {

    const now = new Date();

    const offset =
        now.getTimezoneOffset();

    const localDate =
        new Date(
            now.getTime() -
            offset * 60000
        );

    return localDate
        .toISOString()
        .split("T")[0];

}



// =====================================================
// BULAN SEKARANG
// =====================================================

function bulanSekarang() {

    const now = new Date();

    const tahun =
        now.getFullYear();

    const bulan =
        String(
            now.getMonth() + 1
        ).padStart(2, "0");

    return `${tahun}-${bulan}`;

}



// =====================================================
// INIT
// =====================================================

document.addEventListener(
    "DOMContentLoaded",
    function() {

        document.getElementById(
            "bulan"
        ).value = bulanSekarang();


        document.getElementById(
            "tanggal"
        ).value = tanggalHariIni();


        loadData();

        loadAnalytics();


        document.getElementById(
            "bulan"
        ).addEventListener(
            "change",
            function() {

                loadData();

                loadAnalytics();

            }
        );


        document.getElementById(
            "transactionForm"
        ).addEventListener(
            "submit",
            simpanTransaksi
        );

    }
);



// =====================================================
// LOAD DATA
// =====================================================

async function loadData() {

    try {

        const response =
            await fetch(
                "/api/transaksi"
            );


        if (!response.ok) {

            throw new Error(
                "Gagal mengambil data"
            );

        }


        transaksiData =
            await response.json();


        tampilkanTransaksi();

        loadStatistik();

    }

    catch (error) {

        console.error(error);

        showToast(
            "Gagal memuat data"
        );

    }

}



// =====================================================
// STATISTIK
// =====================================================

async function loadStatistik() {

    const bulan =
        document.getElementById(
            "bulan"
        ).value;


    if (!bulan) return;


    try {

        const response =
            await fetch(
                `/api/statistik?bulan=${bulan}`
            );


        const data =
            await response.json();


        document.getElementById(
            "saldo"
        ).textContent =
            formatRupiah(data.saldo);


        document.getElementById(
            "pemasukan"
        ).textContent =
            formatRupiah(data.pemasukan);


        document.getElementById(
            "pengeluaran"
        ).textContent =
            formatRupiah(data.pengeluaran);


        document.getElementById(
            "jumlahTransaksi"
        ).textContent =
            data.jumlah_transaksi;

    }

    catch (error) {

        console.error(error);

    }

}



// =====================================================
// TRANSAKSI
// =====================================================

function tampilkanTransaksi() {

    const container =
        document.getElementById(
            "transactionList"
        );


    const bulan =
        document.getElementById(
            "bulan"
        ).value;


    const data =
        transaksiData.filter(
            item => {

                return (
                    item.tanggal_transaksi &&
                    item.tanggal_transaksi
                        .startsWith(bulan)
                );

            }
        );


    if (data.length === 0) {

        container.innerHTML = `

            <div class="empty-state">

                <div class="empty-icon">
                    ◌
                </div>

                <h3>
                    Belum ada transaksi
                </h3>

                <p>
                    Tambahkan transaksi pertamamu.
                </p>

            </div>

        `;

        return;

    }


    container.innerHTML =
        data.map(
            item => {

                const income =
                    item.jenis === "pemasukan";


                return `

                <div class="transaction-item">

                    <div class="
                        transaction-icon
                        ${income ? "income" : "expense"}
                    ">

                        ${income ? "↑" : "↓"}

                    </div>


                    <div class="transaction-main">

                        <h4>
                            ${escapeHTML(item.kategori)}
                        </h4>

                        <p>

                            ${escapeHTML(
                                item.keterangan || "Tanpa keterangan"
                            )}

                            •
                            ${formatTanggal(
                                item.tanggal_transaksi
                            )}

                        </p>

                    </div>


                    <div class="
                        transaction-amount
                        ${income ? "income" : "expense"}
                    ">

                        ${income ? "+" : "-"}
                        ${formatRupiah(item.nominal)}

                    </div>


                    <div class="transaction-actions">

                        <button
                            class="small-button"
                            onclick="editTransaksi(${item.id})"
                        >
                            Edit
                        </button>


                        <button
                            class="small-button"
                            onclick="hapusTransaksi(${item.id})"
                        >
                            Hapus
                        </button>

                    </div>

                </div>

                `;

            }
        ).join("");

}



// =====================================================
// FORMAT TANGGAL
// =====================================================

function formatTanggal(tanggal) {

    if (!tanggal) return "-";


    const parts =
        tanggal.split("-");


    if (parts.length !== 3)
        return tanggal;


    return `${parts[2]}/${parts[1]}/${parts[0]}`;

}



// =====================================================
// ESCAPE HTML
// =====================================================

function escapeHTML(value) {

    const div =
        document.createElement("div");

    div.textContent =
        value ?? "";

    return div.innerHTML;

}



// =====================================================
// MODAL
// =====================================================

function bukaModal() {

    document.getElementById(
        "modal"
    ).classList.add("show");


    document.getElementById(
        "modalTitle"
    ).textContent =
        "Tambah Transaksi";


    document.getElementById(
        "transactionForm"
    ).reset();


    document.getElementById(
        "editId"
    ).value = "";


    document.getElementById(
        "tanggal"
    ).value =
        tanggalHariIni();


    pilihJenis("pemasukan");

}



// =====================================================
// TUTUP MODAL
// =====================================================

function tutupModal() {

    document.getElementById(
        "modal"
    ).classList.remove("show");

}


function tutupModalJikaKlikLuar(event) {

    if (
        event.target.id === "modal"
    ) {

        tutupModal();

    }

}



// =====================================================
// PILIH JENIS
// =====================================================

function pilihJenis(jenis) {

    jenisSaatIni = jenis;


    document.getElementById(
        "jenis"
    ).value = jenis;


    const income =
        document.getElementById(
            "incomeButton"
        );


    const expense =
        document.getElementById(
            "expenseButton"
        );


    income.classList.remove(
        "active-income"
    );


    expense.classList.remove(
        "active-expense"
    );


    if (jenis === "pemasukan") {

        income.classList.add(
            "active-income"
        );

    }

    else {

        expense.classList.add(
            "active-expense"
        );

    }

}



// =====================================================
// SIMPAN TRANSAKSI
// =====================================================

async function simpanTransaksi(event) {

    event.preventDefault();


    const editId =
        document.getElementById(
            "editId"
        ).value;


    const data = {

        jenis:
            document.getElementById(
                "jenis"
            ).value,

        kategori:
            document.getElementById(
                "kategori"
            ).value,

        nominal:
            document.getElementById(
                "nominal"
            ).value,

        tanggal_transaksi:
            document.getElementById(
                "tanggal"
            ).value,

        keterangan:
            document.getElementById(
                "keterangan"
            ).value

    };


    try {

        let response;


        if (editId) {

            response =
                await fetch(
                    `/api/transaksi/${editId}`,
                    {

                        method: "PUT",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body:
                            JSON.stringify(data)

                    }
                );

        }

        else {

            response =
                await fetch(
                    "/api/transaksi",
                    {

                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body:
                            JSON.stringify(data)

                    }
                );

        }


        const result =
            await response.json();


        if (!response.ok) {

            throw new Error(
                result.error ||
                "Gagal menyimpan transaksi"
            );

        }


        tutupModal();


        showToast(
            editId
                ? "Transaksi diperbarui"
                : "Transaksi berhasil ditambahkan"
        );


        await loadData();

        await loadAnalytics();

    }

    catch (error) {

        console.error(error);

        showToast(
            error.message
        );

    }

}



// =====================================================
// EDIT
// =====================================================

function editTransaksi(id) {

    const item =
        transaksiData.find(
            x => x.id === id
        );


    if (!item) return;


    document.getElementById(
        "modal"
    ).classList.add("show");


    document.getElementById(
        "modalTitle"
    ).textContent =
        "Edit Transaksi";


    document.getElementById(
        "editId"
    ).value =
        item.id;


    document.getElementById(
        "kategori"
    ).value =
        item.kategori;


    document.getElementById(
        "nominal"
    ).value =
        item.nominal;


    document.getElementById(
        "tanggal"
    ).value =
        item.tanggal_transaksi;


    document.getElementById(
        "keterangan"
    ).value =
        item.keterangan;


    pilihJenis(
        item.jenis
    );

}



// =====================================================
// HAPUS
// =====================================================

async function hapusTransaksi(id) {

    const yakin =
        confirm(
            "Hapus transaksi ini?"
        );


    if (!yakin) return;


    try {

        const response =
            await fetch(
                `/api/transaksi/${id}`,
                {
                    method: "DELETE"
                }
            );


        if (!response.ok) {

            throw new Error(
                "Gagal menghapus"
            );

        }


        showToast(
            "Transaksi dihapus"
        );


        await loadData();

        await loadAnalytics();

    }

    catch (error) {

        console.error(error);

        showToast(
            "Gagal menghapus transaksi"
        );

    }

}



// =====================================================
// HAPUS SEMUA
// =====================================================

async function hapusSemua() {

    if (
        transaksiData.length === 0
    ) {

        showToast(
            "Tidak ada transaksi"
        );

        return;

    }


    const yakin =
        confirm(
            "Yakin ingin menghapus SEMUA transaksi?"
        );


    if (!yakin) return;


    try {

        const response =
            await fetch(
                "/api/transaksi",
                {
                    method: "DELETE"
                }
            );


        if (!response.ok) {

            throw new Error(
                "Gagal menghapus"
            );

        }


        showToast(
            "Semua transaksi dihapus"
        );


        await loadData();

        await loadAnalytics();

    }

    catch (error) {

        console.error(error);

        showToast(
            "Gagal menghapus semua transaksi"
        );

    }

}



// =====================================================
// ANALYTICS
// =====================================================

async function loadAnalytics() {

    const bulan =
        document.getElementById(
            "bulan"
        ).value;


    if (!bulan) return;


    try {

        const response =
            await fetch(
                `/api/analytics?bulan=${bulan}`
            );


        const data =
            await response.json();


        tampilkanCashflowChart(
            data.arus_kas || []
        );


        tampilkanCategoryChart(
            data.kategori || []
        );

    }

    catch (error) {

        console.error(
            "Analytics error:",
            error
        );

    }

}



// =====================================================
// CASHFLOW CHART
// =====================================================

function tampilkanCashflowChart(data) {

    const canvas =
        document.getElementById(
            "cashflowChart"
        );


    const empty =
        document.getElementById(
            "cashflowEmpty"
        );


    if (cashflowChart) {

        cashflowChart.destroy();

        cashflowChart = null;

    }


    if (!data.length) {

        canvas.style.display =
            "none";

        empty.style.display =
            "block";

        return;

    }


    canvas.style.display =
        "block";

    empty.style.display =
        "none";


    cashflowChart =
        new Chart(
            canvas,
            {

                type: "line",

                data: {

                    labels:
                        data.map(
                            x => x.tanggal
                        ),

                    datasets: [

                        {

                            label:
                                "Pemasukan",

                            data:
                                data.map(
                                    x =>
                                        x.pemasukan
                                ),

                            borderColor:
                                "#39d98a",

                            backgroundColor:
                                "rgba(57,217,138,.08)",

                            fill: true,

                            tension: .4,

                            borderWidth: 2,

                            pointRadius: 3

                        },


                        {

                            label:
                                "Pengeluaran",

                            data:
                                data.map(
                                    x =>
                                        x.pengeluaran
                                ),

                            borderColor:
                                "#ff6577",

                            backgroundColor:
                                "rgba(255,101,119,.06)",

                            fill: true,

                            tension: .4,

                            borderWidth: 2,

                            pointRadius: 3

                        }

                    ]

                },


                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    interaction: {

                        mode: "index",

                        intersect: false

                    },


                    plugins: {

                        legend: {

                            labels: {

                                color:
                                    "#9ba4b4",

                                font: {
                                    size: 10
                                }

                            }

                        },


                        tooltip: {

                            callbacks: {

                                label:
                                    function(
                                        context
                                    ) {

                                        return (
                                            context.dataset.label
                                            + ": "
                                            +
                                            formatRupiah(
                                                context.raw
                                            )
                                        );

                                    }

                            }

                        }

                    },


                    scales: {

                        x: {

                            grid: {
                                display: false
                            },

                            ticks: {
                                color: "#697386"
                            }

                        },


                        y: {

                            grid: {

                                color:
                                    "rgba(255,255,255,.05)"

                            },

                            ticks: {

                                color:
                                    "#697386",

                                callback:
                                    function(
                                        value
                                    ) {

                                        if (
                                            value >=
                                            1000000
                                        ) {

                                            return (
                                                "Rp " +
                                                (
                                                    value /
                                                    1000000
                                                ).toFixed(1)
                                                +
                                                " jt"
                                            );

                                        }


                                        if (
                                            value >=
                                            1000
                                        ) {

                                            return (
                                                "Rp " +
                                                (
                                                    value /
                                                    1000
                                                ).toFixed(0)
                                                +
                                                " rb"
                                            );

                                        }


                                        return value;

                                    }

                            }

                        }

                    }

                }

            }
        );

}



// =====================================================
// CATEGORY CHART
// =====================================================

function tampilkanCategoryChart(data) {

    const canvas =
        document.getElementById(
            "categoryChart"
        );


    const empty =
        document.getElementById(
            "categoryEmpty"
        );


    const legend =
        document.getElementById(
            "categoryLegend"
        );


    if (categoryChart) {

        categoryChart.destroy();

        categoryChart = null;

    }


    legend.innerHTML = "";


    if (!data.length) {

        canvas.style.display =
            "none";

        empty.style.display =
            "block";

        return;

    }


    canvas.style.display =
        "block";

    empty.style.display =
        "none";


    const labels =
        data.map(
            x => x.kategori
        );


    const values =
        data.map(
            x => x.total
        );


    const colors = [

        "#6c8cff",

        "#9b7cff",

        "#39d98a",

        "#ff6577",

        "#ffc857",

        "#55c2ff",

        "#ff8fab",

        "#b5e48c"

    ];


    categoryChart =
        new Chart(
            canvas,
            {

                type: "doughnut",

                data: {

                    labels,

                    datasets: [

                        {

                            data: values,

                            backgroundColor:
                                labels.map(
                                    (_, i) =>
                                        colors[
                                            i %
                                            colors.length
                                        ]
                                ),

                            borderWidth: 0

                        }

                    ]

                },


                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    cutout: "72%",


                    plugins: {

                        legend: {
                            display: false
                        },


                        tooltip: {

                            callbacks: {

                                label:
                                    function(
                                        context
                                    ) {

                                        return (
                                            context.label
                                            + ": "
                                            +
                                            formatRupiah(
                                                context.raw
                                            )
                                        );

                                    }

                            }

                        }

                    }

                }

            }
        );


    data.forEach(
        (item, index) => {

            legend.innerHTML += `

                <div class="legend-item">

                    <div class="legend-name">

                        <span
                            class="legend-dot"
                            style="
                                background:
                                ${colors[
                                    index %
                                    colors.length
                                ]}
                            "
                        ></span>

                        ${escapeHTML(
                            item.kategori
                        )}

                    </div>

                    <strong>
                        ${formatRupiah(
                            item.total
                        )}
                    </strong>

                </div>

            `;

        }
    );

}



// =====================================================
// TOAST
// =====================================================

function showToast(message) {

    const toast =
        document.getElementById(
            "toast"
        );


    document.getElementById(
        "toastMessage"
    ).textContent =
        message;


    toast.classList.add(
        "show"
    );


    setTimeout(
        function() {

            toast.classList.remove(
                "show"
            );

        },
        2500
    );

}
