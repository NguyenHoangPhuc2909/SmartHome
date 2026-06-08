const fs = require('fs');
const path = require('path');

function walk(dir, callback) {
  fs.readdirSync(dir).forEach(f => {
    let dirPath = path.join(dir, f);
    if (fs.statSync(dirPath).isDirectory()) {
      walk(dirPath, callback);
    } else {
      callback(dirPath);
    }
  });
}

walk(path.join(__dirname, 'src'), (filePath) => {
  if (filePath.endsWith('.jsx') || filePath.endsWith('.js')) {
    let content = fs.readFileSync(filePath, 'utf8');
    let original = content;

    // 1. primaryTypographyProps -> disableTypography + Typography
    // Example: <ListItemText primary={item.text} primaryTypographyProps={{ fontWeight: 600 }} />
    // We will just do a generic replacement for this specific file Layout.jsx
    if (filePath.includes('Layout.jsx') && content.includes('primaryTypographyProps')) {
      content = content.replace(
        /<ListItemText\s*\n\s*primary=\{([^}]+)\}\s*\n\s*primaryTypographyProps=\{\{([^}]+)\}\}\s*\n\s*\/>/g,
        '<ListItemText disableTypography primary={<Typography sx={{$2}}>{$1}</Typography>} />'
      );
    }

    // 2. InputProps={{ inputProps: { ... } }} -> inputProps={{ ... }}
    content = content.replace(/InputProps=\{\{\s*inputProps:\s*(\{.*?\})\s*\}\}/g, 'inputProps={$1}');

    // 3. PaperProps={{ sx: ... }} -> slotProps={{ paper: { sx: ... } }}
    content = content.replace(/PaperProps=\{\{(.*?)\}\}/g, 'slotProps={{ paper: { $1 } }}');

    // 4. <Grid alignItems="..." -> <Grid sx={{ alignItems: '...' }}
    // Needs to handle if sx already exists or not. 
    // Actually, in Access.jsx line 109 it's exactly: <Grid container spacing={4} alignItems="center">
    if (content.includes('alignItems="center"')) {
        content = content.replace(/<Grid container spacing=\{4\} alignItems="center">/g, '<Grid container spacing={4} sx={{ alignItems: \'center\' }}>');
    }

    // 5. <Grid item xs=...
    // Let's just remove the word "item"
    content = content.replace(/<Grid\s+item/g, '<Grid');

    if (content !== original) {
      fs.writeFileSync(filePath, content, 'utf8');
      console.log('Updated: ' + filePath);
    }
  }
});
