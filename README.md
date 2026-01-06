# Demo Lắp Ráp Genome

Ứng dụng giáo dục minh họa 2 thuật toán genome assembly:

- **OLC** (Overlap-Layout-Consensus) - dựa trên đường đi Hamilton
- **DBG** (de Bruijn Graph) - dựa trên đường đi Euler

## Tính năng

- Tạo genome ngẫu nhiên hoặc chọn từ ví dụ virus thật
- Phân mảnh genome thành reads với coverage tùy chỉnh
- Visualization đồ thị overlap (OLC) và de Bruijn (DBG)
- Animation từng bước thuật toán
- So sánh kết quả giữa 2 thuật toán

## Cài đặt

```bash
# Clone repo
git clone <repo-url>
cd genome-assembly

# Tạo virtual environment
python -m venv ~/.venvs/genome-assembly
source ~/.venvs/genome-assembly/bin/activate

# Cài đặt dependencies
pip install -r requirements.txt
```

## Chạy ứng dụng

```bash
streamlit run app.py
```

Truy cập: http://localhost:8501

## Cấu trúc project

```
genome-assembly/
├── app.py                  # Main Streamlit app
├── requirements.txt
├── src/
│   ├── genome/             # Genome generation & processing
│   │   ├── generator.py    # Random genome, virus examples
│   │   ├── fragmenter.py   # Read fragmentation
│   │   └── validator.py    # DNA validation
│   ├── assembly/           # Assembly algorithms
│   │   ├── olc.py          # OLC (Overlap-Layout-Consensus)
│   │   ├── dbg.py          # DBG (de Bruijn Graph)
│   │   └── metrics.py      # Quality metrics (N50, accuracy)
│   ├── visualization/      # Visualization components
│   │   ├── graph_viz.py    # PyVis graph rendering
│   │   ├── sequence_viz.py # Plotly sequence display
│   │   └── animator.py     # Step-by-step animation
│   └── ui/                 # Streamlit UI components
│       ├── controls.py     # Sidebar widgets
│       └── tabs.py         # Tab components
├── tests/                  # Unit tests
└── data/
    └── virus_examples.json # Sample virus genomes
```

## Sử dụng

1. **Tạo genome**: Chọn phương thức nhập (ngẫu nhiên/virus/thủ công)
2. **Cấu hình**: Điều chỉnh độ dài read, coverage, thuật toán
3. **Chạy**: Nhấn "Chạy lắp ráp"
4. **Xem kết quả**: Chuyển giữa các tab để xem từng bước

## Chạy tests

```bash
pytest tests/ -v
```

## Thuật toán

### OLC (Overlap-Layout-Consensus)

1. **Overlap**: Tìm suffix-prefix matches giữa reads
2. **Layout**: Xây dựng overlap graph, tìm đường Hamilton
3. **Consensus**: Ghép reads theo đường đi

### de Bruijn Graph

1. **K-mers**: Tạo k-mers từ reads
2. **Graph**: Nodes = (k-1)-mers, Edges = k-mers
3. **Euler**: Tìm đường Euler (Hierholzer algorithm)
4. **Reconstruct**: Ghép path thành genome

## Yêu cầu

- Python >= 3.9
- Streamlit >= 1.28.0
- PyVis >= 0.3.2
- Plotly >= 5.18.0
