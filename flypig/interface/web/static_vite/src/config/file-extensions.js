/**
 * file-extensions.js — 文件扩展名分类，用于 EditorPane 路由
 *
 * 数据与代码分离：扩展名分类表属于配置数据，统一放在 config/ 下维护，
 * 组件只做 includes 查询，不内嵌列表。
 */
export const CODE_EXTENSIONS = [
  'js','ts','jsx','tsx','vue','py','json','md','html','css','scss','less',
  'yml','yaml','toml','xml','sh','bash','go','rs','java','kt',
  'c','cpp','h','hpp','sql','rb','php','r','txt','gitignore','ini','cfg',
  'env','bat','ps1','conf','log','dockerfile',
]

export const DOC_EXTENSIONS = ['docx','pdf','xlsx','pptx']

export const IMAGE_EXTENSIONS = ['png','jpg','jpeg','gif','svg','webp','ico','bmp']
