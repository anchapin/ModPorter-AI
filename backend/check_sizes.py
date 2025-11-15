import os

def main():
    services_dir = "src/services"
    files = [f for f in os.listdir(services_dir) if f.endswith('.py') and f != '__init__.py']
    
    # Get file sizes
    file_sizes = []
    for f in files:
        filepath = os.path.join(services_dir, f)
        size = os.path.getsize(filepath)
        file_sizes.append((f, size))
    
    # Sort by size (largest first)
    file_sizes.sort(key=lambda x: x[1], reverse=True)
    
    print('High impact service files by size:')
    for i, (filename, size) in enumerate(file_sizes[:10], 1):
        print(f'{i}. {filename}: {size} bytes')

if __name__ == "__main__":
    main()
