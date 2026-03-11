package com.filemanager;

import org.apache.poi.hwpf.HWPFDocument;
import org.apache.poi.hwpf.extractor.WordExtractor;
import org.apache.poi.hssf.usermodel.HSSFWorkbook;
import org.apache.poi.hssf.usermodel.HSSFSheet;
import org.apache.poi.hssf.usermodel.HSSFRow;
import org.apache.poi.hssf.usermodel.HSSFCell;
import org.apache.poi.ss.usermodel.CellType;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.apache.poi.xssf.usermodel.XSSFSheet;
import org.apache.poi.xssf.usermodel.XSSFRow;
import org.apache.poi.xssf.usermodel.XSSFCell;
import org.apache.poi.xwpf.usermodel.XWPFDocument;
import org.apache.poi.xwpf.usermodel.XWPFParagraph;
import org.apache.poi.xwpf.usermodel.XWPFTable;
import org.apache.poi.xwpf.usermodel.XWPFTableRow;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.rendering.PDFRenderer;
import org.apache.pdfbox.text.PDFTextStripper;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;

/**
 * Office 和 PDF 文档转换工具
 * 支持：Word/Excel 转 HTML，PDF 转 PNG 图片
 */
public class POIConverter {

    public static void main(String[] args) {
        if (args.length < 3) {
            printUsage();
            System.exit(1);
        }

        String command = args[0];
        String inputPath = args[1];
        String outputPath = args[2];
        String originalFileName = args.length > 3 ? args[3] : new File(inputPath).getName();

        try {
            switch (command) {
                case "word2html":
                    convertWordToHtml(inputPath, outputPath, originalFileName);
                    break;
                case "excel2html":
                    convertExcelToHtml(inputPath, outputPath, originalFileName);
                    break;
                case "pdf2html":
                    convertPdfToHtml(inputPath, outputPath);
                    break;
                case "pdf2images":
                    convertPdfToImages(inputPath, outputPath);
                    break;
                default:
                    System.err.println("未知命令: " + command);
                    printUsage();
                    System.exit(1);
            }
            System.exit(0);
        } catch (Exception e) {
            System.err.println("转换失败: " + e.getMessage());
            e.printStackTrace();
            System.exit(1);
        }
    }

    private static void printUsage() {
        System.out.println("用法:");
        System.out.println("  java -jar poi-converter.jar word2html <输入.docx> <输出.html>");
        System.out.println("  java -jar poi-converter.jar excel2html <输入.xlsx> <输出.html>");
        System.out.println("  java -jar poi-converter.jar pdf2html <输入.pdf> <输出.html>");
        System.out.println("  java -jar poi-converter.jar pdf2images <输入.pdf> <输出目录>");
    }

    /**
     * Word 文档转 HTML
     */
    private static void convertWordToHtml(String inputPath, String outputPath, String originalFileName) throws Exception {
        StringBuilder html = new StringBuilder();
        html.append("<!DOCTYPE html>\n");
        html.append("<html><head><meta charset='UTF-8'>");
        html.append("<style>");
        html.append("body { font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; line-height: 1.6; }");
        html.append("p { margin: 8px 0; text-indent: 2em; }");
        html.append("table { border-collapse: collapse; width: 100%; margin: 10px 0; }");
        html.append("td, th { border: 1px solid #ddd; padding: 8px; text-align: left; }");
        html.append("th { background-color: #f2f2f2; font-weight: bold; }");
        html.append("</style></head><body>");

        // 使用原始文件名作为标题
        html.append("<h2>").append(escapeHtml(originalFileName)).append("</h2>");

        if (inputPath.toLowerCase().endsWith(".docx")) {
            try (XWPFDocument document = new XWPFDocument(new FileInputStream(inputPath))) {
                for (XWPFParagraph paragraph : document.getParagraphs()) {
                    String text = paragraph.getText().trim();
                    if (!text.isEmpty()) {
                        html.append("<p>").append(escapeHtml(text)).append("</p>");
                    }
                }
                for (XWPFTable table : document.getTables()) {
                    html.append("<table>");
                    for (XWPFTableRow row : table.getRows()) {
                        html.append("<tr>");
                        row.getTableCells().forEach(cell -> {
                            html.append("<td>").append(escapeHtml(cell.getText().trim())).append("</td>");
                        });
                        html.append("</tr>");
                    }
                    html.append("</table>");
                }
            }
        } else {
            try (HWPFDocument document = new HWPFDocument(new FileInputStream(inputPath));
                 WordExtractor extractor = new WordExtractor(document)) {
                for (String paragraph : extractor.getParagraphText()) {
                    String text = paragraph.trim();
                    if (!text.isEmpty()) {
                        html.append("<p>").append(escapeHtml(text)).append("</p>");
                    }
                }
            }
        }

        html.append("</body></html>");
        Files.write(Paths.get(outputPath), html.toString().getBytes(StandardCharsets.UTF_8));
    }

    /**
     * Excel 文档转 HTML
     */
    private static void convertExcelToHtml(String inputPath, String outputPath, String originalFileName) throws Exception {
        StringBuilder html = new StringBuilder();
        html.append("<!DOCTYPE html>\n");
        html.append("<html><head><meta charset='UTF-8'>");
        html.append("<style>");
        html.append("body { font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; }");
        html.append("h2 { color: #333; border-bottom: 2px solid #409eff; padding-bottom: 10px; }");
        html.append(".sheet { margin-bottom: 30px; }");
        html.append(".sheet h3 { color: #666; margin-bottom: 10px; }");
        html.append("table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 14px; }");
        html.append("td, th { border: 1px solid #ddd; padding: 8px 12px; text-align: left; white-space: pre-wrap; }");
        html.append("th { background-color: #f2f2f2; font-weight: bold; color: #333; }");
        html.append("tr:nth-child(even) { background-color: #f9f9f9; }");
        html.append("</style></head><body>");

        // 使用原始文件名作为标题
        html.append("<h2>").append(escapeHtml(originalFileName)).append("</h2>");

        if (inputPath.toLowerCase().endsWith(".xlsx")) {
            try (XSSFWorkbook workbook = new XSSFWorkbook(new FileInputStream(inputPath))) {
                for (int sheetIndex = 0; sheetIndex < workbook.getNumberOfSheets(); sheetIndex++) {
                    XSSFSheet sheet = workbook.getSheetAt(sheetIndex);
                    html.append("<div class='sheet'>");
                    html.append("<h3>").append(escapeHtml(sheet.getSheetName())).append("</h3>");
                    html.append("<table>");

                    for (int rowIndex = 0; rowIndex <= sheet.getLastRowNum(); rowIndex++) {
                        XSSFRow row = sheet.getRow(rowIndex);
                        if (row == null) continue;

                        html.append("<tr>");
                        short lastCellNum = row.getLastCellNum();
                        for (int colIndex = 0; colIndex < lastCellNum; colIndex++) {
                            XSSFCell cell = row.getCell(colIndex);
                            String cellValue = getCellValueAsString(cell);
                            html.append("<td>").append(escapeHtml(cellValue)).append("</td>");
                        }
                        html.append("</tr>");
                    }
                    html.append("</table></div>");
                }
            }
        } else {
            try (HSSFWorkbook workbook = new HSSFWorkbook(new FileInputStream(inputPath))) {
                for (int sheetIndex = 0; sheetIndex < workbook.getNumberOfSheets(); sheetIndex++) {
                    HSSFSheet sheet = workbook.getSheetAt(sheetIndex);
                    html.append("<div class='sheet'>");
                    html.append("<h3>").append(escapeHtml(sheet.getSheetName())).append("</h3>");
                    html.append("<table>");

                    for (int rowIndex = 0; rowIndex <= sheet.getLastRowNum(); rowIndex++) {
                        HSSFRow row = sheet.getRow(rowIndex);
                        if (row == null) continue;

                        html.append("<tr>");
                        short lastCellNum = row.getLastCellNum();
                        for (int colIndex = 0; colIndex < lastCellNum; colIndex++) {
                            HSSFCell cell = row.getCell(colIndex);
                            String cellValue = getCellValueAsString(cell);
                            html.append("<td>").append(escapeHtml(cellValue)).append("</td>");
                        }
                        html.append("</tr>");
                    }
                    html.append("</table></div>");
                }
            }
        }

        html.append("</body></html>");
        Files.write(Paths.get(outputPath), html.toString().getBytes(StandardCharsets.UTF_8));
    }

    /**
     * PDF 文档转 HTML（文本提取）
     */
    private static void convertPdfToHtml(String inputPath, String outputPath) throws Exception {
        StringBuilder html = new StringBuilder();
        html.append("<!DOCTYPE html>\n");
        html.append("<html><head><meta charset='UTF-8'>");
        html.append("<style>");
        html.append("body { font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; line-height: 1.8; }");
        html.append("h2 { color: #333; border-bottom: 2px solid #409eff; padding-bottom: 10px; }");
        html.append(".page { margin-bottom: 30px; padding: 20px; background: #fff; border: 1px solid #eee; }");
        html.append(".page-header { font-size: 14px; color: #999; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px dashed #ddd; }");
        html.append("p { margin: 10px 0; text-align: justify; }");
        html.append("</style></head><body>");

        String fileName = new File(inputPath).getName();
        html.append("<h2>").append(escapeHtml(fileName)).append("</h2>");

        // PDFBox 3.0.x 使用新的加载方式
        try (PDDocument document = PDDocument.load(new File(inputPath))) {
            int totalPages = document.getNumberOfPages();
            org.apache.pdfbox.text.PDFTextStripper stripper = new org.apache.pdfbox.text.PDFTextStripper();

            for (int pageNum = 1; pageNum <= totalPages; pageNum++) {
                stripper.setStartPage(pageNum);
                stripper.setEndPage(pageNum);
                String pageText = stripper.getText(document);

                html.append("<div class='page'>");
                html.append("<div class='page-header'>第 ").append(pageNum).append(" 页 / 共 ").append(totalPages).append(" 页</div>");

                String[] paragraphs = pageText.split("\\r?\\n\\r?\\n");
                for (String para : paragraphs) {
                    String trimmed = para.trim().replaceAll("\\r?\\n", " ");
                    if (!trimmed.isEmpty()) {
                        html.append("<p>").append(escapeHtml(trimmed)).append("</p>");
                    }
                }
                html.append("</div>");
            }
        }

        html.append("</body></html>");
        Files.write(Paths.get(outputPath), html.toString().getBytes(StandardCharsets.UTF_8));
    }

    /**
     * PDF 转图片（每页转一张 PNG）
     * 输出路径是目录，每页保存为 page_1.png, page_2.png, ...
     */
    private static void convertPdfToImages(String inputPath, String outputDir) throws Exception {
        File outputDirFile = new File(outputDir);
        if (!outputDirFile.exists()) {
            outputDirFile.mkdirs();
        }

        // PDFBox 3.0.x 使用新的加载方式
        try (PDDocument document = PDDocument.load(new File(inputPath))) {
            int totalPages = document.getNumberOfPages();
            PDFRenderer renderer = new PDFRenderer(document);

            // DPI 设置：150 DPI 平衡速度和质量
            float dpi = 150;

            for (int pageNum = 0; pageNum < totalPages; pageNum++) {
                // 渲染页面为图片
                BufferedImage image = renderer.renderImageWithDPI(pageNum, dpi);

                // 输出文件
                File outputFile = new File(outputDirFile, String.format("page_%d.png", pageNum + 1));
                ImageIO.write(image, "png", outputFile);

                System.err.println("已转换第 " + (pageNum + 1) + " 页，共 " + totalPages + " 页");
            }

            // 输出页数信息（用于 Python 读取）
            File infoFile = new File(outputDirFile, "info.txt");
            Files.write(infoFile.toPath(), String.valueOf(totalPages).getBytes(StandardCharsets.UTF_8));
        }
    }

    /**
     * 获取单元格值（支持多种类型）
     */
    private static String getCellValueAsString(org.apache.poi.ss.usermodel.Cell cell) {
        if (cell == null) {
            return "";
        }

        CellType cellType = cell.getCellType();
        switch (cellType) {
            case STRING:
                return cell.getStringCellValue().trim();
            case NUMERIC:
                double numValue = cell.getNumericCellValue();
                if (numValue == (long) numValue) {
                    return String.valueOf((long) numValue);
                } else {
                    return String.valueOf(numValue);
                }
            case BOOLEAN:
                return String.valueOf(cell.getBooleanCellValue());
            case FORMULA:
                try {
                    return String.valueOf(cell.getNumericCellValue());
                } catch (Exception e) {
                    return cell.getCellFormula();
                }
            default:
                return "";
        }
    }

    /**
     * HTML 转义
     */
    private static String escapeHtml(String text) {
        if (text == null) {
            return "";
        }
        return text.replace("&", "&amp;")
                   .replace("<", "&lt;")
                   .replace(">", "&gt;")
                   .replace("\"", "&quot;")
                   .replace("'", "&#x27;")
                   .replace(" ", "&nbsp;");
    }
}
