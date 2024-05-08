import React from "react";

const Loading = ({ text = "" }) => {
  return (
    <div className="flex flex-col justify-center items-center h-screen">
      <div className="animate-spin rounded-full h-32 w-32 border-t-2 border-b-2 border-purple"></div>
      {text && <p className="mt-4 text-lg text-purple-700">{text}</p>}
    </div>
  );
};

export default Loading;
