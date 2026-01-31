# 🎮 Minecraft Java → Bedrock Transpiler

Ferramenta web completa para converter mods do Minecraft Java Edition para addons do Bedrock Edition.

## 🚀 Características

- ✅ **Análise automática** de bytecode Java
- ✅ **Conversão de items** com componentes Bedrock
- ✅ **Conversão de receitas** (incluindo extreme crafting 9x9)
- ✅ **Geração de scripts** JavaScript para comportamentos customizados
- ✅ **Extração de assets** (texturas, modelos, sons)
- ✅ **Interface web moderna** com drag & drop
- ✅ **Progresso em tempo real**
- ✅ **Download direto** do .mcaddon

## 📁 Estrutura do Projeto

```
minecraft-transpiler-web/
├── backend/
│   ├── app.py                 # Servidor Flask
│   ├── transpiler_engine.py   # Motor de conversão
│   ├── config.py              # Configurações
│   └── requirements.txt       # Dependências Python
├── frontend/
│   ├── index.html             # Interface HTML
│   ├── css/
│   │   └── style.css          # Estilos
│   └── js/
│       └── app.js             # Lógica JavaScript
├── uploads/                   # Arquivos temporários (upload)
├── outputs/                   # Arquivos temporários (resultado)
└── README.md
```

## 🛠️ Instalação

### Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

### Passo a Passo

1. **Clone ou baixe o projeto**
```bash
cd minecraft-transpiler-web
```

2. **Crie as pastas necessárias**
```bash
mkdir -p backend frontend/css frontend/js uploads outputs
```

3. **Organize os arquivos**
- Coloque `app.py`, `transpiler_engine.py`, `config.py`, `requirements.txt` na pasta `backend/`
- Coloque `index.html` na pasta `frontend/`
- Coloque `style.css` na pasta `frontend/css/`
- Coloque `app.js` na pasta `frontend/js/`

4. **Instale as dependências**
```bash
cd backend
pip install -r requirements.txt
```

## ▶️ Como Usar

### 1. Inicie o servidor

```bash
cd backend
python app.py
```

Você verá:
```
* Running on http://0.0.0.0:5000
```

### 2. Acesse a interface web

Abra seu navegador e acesse:
```
http://localhost:5000
```

### 3. Converta um mod

1. Arraste um arquivo `.jar` do mod para a área de upload
2. Aguarde o processamento (você verá o progresso em tempo real)
3. Quando concluído, clique em "Baixar .mcaddon"
4. Instale o addon no Minecraft Bedrock

## 📊 O que o Transpiler Converte

### ✅ Items
- Durabilidade (incluindo "indestrutível" → MAX_VALUE)
- Stack size
- Dano de ataque
- Velocidade de mineração
- Armadura e resistência
- Propriedades de comida
- Encantabilidade

### ✅ Receitas
- Shaped (3x3)
- Shapeless
- Extreme Crafting (9x9) → Cria UI customizada

### ✅ Comportamentos Especiais
- Instant kill → Script de dano massivo
- Instant break → Script de quebra instantânea
- Inventory tick → Efeitos passivos
- Custom attacks → Lógica de ataque customizada

### ✅ Assets
- Texturas (.png)
- Modelos (.json)
- Sons (.ogg)

## 🔧 API Endpoints

### Upload
```
POST /api/upload
Body: multipart/form-data (file)
Response: { job_id, filename, message }
```

### Status
```
GET /api/status/{job_id}
Response: { status, progress, message, stats, ... }
```

### Download
```
GET /api/download/{job_id}
Response: arquivo .mcaddon
```

### Health Check
```
GET /api/health
Response: { status, timestamp, version }
```

## ⚙️ Configuração

Edite `backend/config.py` para ajustar:

```python
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
UPLOAD_FOLDER = '../uploads'
OUTPUT_FOLDER = '../outputs'
```

## 🐛 Troubleshooting

### Erro: "Module not found"
```bash
pip install -r requirements.txt
```

### Erro: "Port already in use"
Altere a porta em `app.py`:
```python
app.run(port=5001)  # Use outra porta
```

### Erro: "CORS policy"
Verifique se `Flask-CORS` está instalado:
```bash
pip install Flask-CORS
```

## 📝 Limitações Conhecidas

1. **Modelos 3D**: Conversão simplificada (requer biblioteca adicional)
2. **Mecânicas complexas**: Algumas podem precisar ajuste manual
3. **Código Java nativo**: Não converte código JNI ou bibliotecas externas
4. **Tamanho**: Limite de 100MB por arquivo

## 🔮 Melhorias Futuras

- [ ] Conversão avançada de modelos 3D
- [ ] Suporte para blocos customizados
- [ ] Preview do addon antes do download
- [ ] Histórico de conversões
- [ ] Autenticação de usuários
- [ ] Database para persistência

## 📄 Licença

Este projeto é fornecido "como está" para uso educacional e da comunidade Minecraft.

## 🤝 Contribuindo

Contribuições são bem-vindas! Sinta-se livre para:
- Reportar bugs
- Sugerir melhorias
- Enviar pull requests

## 👨‍💻 Autor

Desenvolvido com 💚 por **Masterotaku** para a comunidade Minecraft

## 📞 Suporte

Para problemas ou dúvidas:
1. Verifique a seção de Troubleshooting
2. Consulte os logs no terminal
3. Abra uma issue no repositório

---

**Versão**: 1.0.0  
**Última atualização**: Janeiro 2025
