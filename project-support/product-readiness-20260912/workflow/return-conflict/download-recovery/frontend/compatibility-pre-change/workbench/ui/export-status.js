export function exportStatusText(status){
 const revision=status.saved_revision!=null, label=revision?'revision':'event';
 const saved=revision?status.saved_revision:status.saved_event_cursor, exported=revision?status.exported_revision:status.event_cursor;
 const version=saved==null?'':' · saved '+label+' '+saved;
 const snapshot=exported==null?'':' · Excel '+label+' '+exported;
 const labels={current:'Decisions saved · Excel synchronized',pending:'Decisions saved · Excel pending',refreshing:'Decisions saved · Excel synchronizing',failed:'Decisions saved · Excel sync failed; retry scheduled',unknown:'Excel synchronization status unavailable'};
 return (labels[status.status]||'Excel preparing in background')+version+snapshot+(status.message?' · '+status.message:'');
}
