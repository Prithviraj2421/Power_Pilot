import React from 'react';
import { Card } from '../../../components/ui/Card';
import { Badge } from '../../../components/ui/Badge';
import { Monitor, Download, Code, FileSpreadsheet } from 'lucide-react';

export const PowerBIInstructionGuide: React.FC = () => {
  return (
    <Card glass className="p-6 border-primary/30">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-border">
        <h3 className="text-lg font-bold text-white flex items-center gap-2">
          <Monitor className="w-5 h-5 text-primary" />
          <span>How to Connect PowerPilot to Power BI Desktop</span>
        </h3>
        <Badge variant="primary">3 Integration Options</Badge>
      </div>

      <p className="text-xs text-gray-400 mb-4">
        All three start the same way: download the <strong>Cleaned Dataset (CSV)</strong> from the
        Export Center, then load it into Power BI as a table named exactly as shown in the header of
        the exported script. The measures refer to that table by name.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-sm">
        {/* Method 1: Power Query M, then DAX measures */}
        <div className="p-4 bg-surface rounded-xl border border-border space-y-2">
          <div className="flex items-center gap-2 font-bold text-white">
            <FileSpreadsheet className="w-4 h-4 text-warning" />
            <span>Option 1: Load the data (Power Query M)</span>
          </div>
          <p className="text-xs text-gray-300">
            In Power BI Desktop choose <strong>Get Data → Blank Query → Advanced Editor</strong>, paste the M
            code, and set <code>FilePath</code> to where you saved the cleaned CSV. Rename the query to the
            table name given in the script&apos;s comments.
          </p>
        </div>

        {/* Method 2: DAX measures */}
        <div className="p-4 bg-surface rounded-xl border border-border space-y-2">
          <div className="flex items-center gap-2 font-bold text-white">
            <Code className="w-4 h-4 text-purple-400" />
            <span>Option 2: Add the DAX measures</span>
          </div>
          <p className="text-xs text-gray-300">
            With the table loaded, choose <strong>Modeling → New measure</strong> and paste one measure at a
            time: each line of the <code>.dax</code> file that looks like <code>Name = formula</code>. The
            comment lines above each measure explain what it tells you.
          </p>
        </div>

        {/* Method 3: BIM */}
        <div className="p-4 bg-surface rounded-xl border border-border space-y-2 md:col-span-2">
          <div className="flex items-center gap-2 font-bold text-white">
            <Download className="w-4 h-4 text-success" />
            <span>Option 3: Open the Tabular Model (.bim) in Tabular Editor</span>
          </div>
          <p className="text-xs text-gray-300">
            The <code>.bim</code> file defines the table, its Power Query source and every measure in one go.
            Open it in <strong>Tabular Editor</strong> (File → Open → From File), set <code>FilePath</code> in
            the table&apos;s partition, then deploy it to Power BI Desktop or Analysis Services. Power BI
            Desktop cannot open a <code>.bim</code> file directly.
          </p>
        </div>
      </div>
    </Card>
  );
};
