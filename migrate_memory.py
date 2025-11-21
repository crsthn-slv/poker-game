#!/usr/bin/env python3
"""
Script para migrar arquivos de memória para o diretório centralizado data/memory/
"""
import os
import shutil
import glob
from pathlib import Path

def migrate_memory_files():
    """Move todos os arquivos de memória para data/memory/"""
    # Diretório raiz do projeto
    project_root = Path(__file__).parent
    memory_dir = project_root / 'data' / 'memory'
    
    # Cria diretório se não existir
    memory_dir.mkdir(parents=True, exist_ok=True)
    
    # Locais onde podem estar os arquivos de memória
    search_locations = [
        project_root,  # Raiz do projeto
        project_root / 'web',  # Diretório web
    ]
    
    moved_count = 0
    skipped_count = 0
    
    print("Migrando arquivos de memória para data/memory/...")
    print("-" * 50)
    
    for location in search_locations:
        if not location.exists():
            continue
            
        # Encontra todos os arquivos de memória
        memory_files = list(location.glob('*_memory.json'))
        
        for memory_file in memory_files:
            target_file = memory_dir / memory_file.name
            
            # Se já existe no destino, verifica qual é mais recente
            if target_file.exists():
                if memory_file.stat().st_mtime > target_file.stat().st_mtime:
                    # Arquivo atual é mais recente, substitui
                    print(f"  Atualizando: {memory_file.name} (mais recente)")
                    shutil.copy2(memory_file, target_file)
                    memory_file.unlink()  # Remove arquivo antigo
                    moved_count += 1
                else:
                    # Arquivo no destino é mais recente, apenas remove o antigo
                    print(f"  Mantendo: {memory_file.name} (já existe versão mais recente)")
                    memory_file.unlink()
                    skipped_count += 1
            else:
                # Move arquivo para destino
                print(f"  Movendo: {memory_file.name}")
                shutil.move(str(memory_file), str(target_file))
                moved_count += 1
    
    print("-" * 50)
    print(f"Migração concluída!")
    print(f"  Arquivos movidos/atualizados: {moved_count}")
    print(f"  Arquivos mantidos (já existiam): {skipped_count}")
    print(f"  Localização: {memory_dir}")

if __name__ == '__main__':
    migrate_memory_files()

