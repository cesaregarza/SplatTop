import React from "react";

const Contact = () => {
    return (
        <div className="container mx-auto px-4">
        <h1 className="text-2xl font-bold text-white mt-8">Contact Us</h1>
        <p className="text-white mt-4">
            If you have any questions or concerns, please feel free to contact us
            using the form below.
        </p>
        <form className="mt-8">
            <div className="flex flex-col md:flex-row space-y-4 md:space-x-4 md:space-y-0">
            <div className="flex flex-col w-full">
                <label htmlFor="name" className="text-white">
                Name
                </label>
                <input
                type="text"
                id="name"
                name="name"
                className="input"
                placeholder="Your Name"
                />
            </div>
            <div className="flex flex-col w-full">
                <label htmlFor="email" className="text-white">
                Email
                </label>
                <input
                type="email"
                id="email"
                name="email"
                className="input"
                placeholder="Your Email"
                />
            </div>
            </div>
            <div className="flex flex-col mt-4">
            <label htmlFor="message" className="text-white">
                Message
            </label>
            <textarea
                id="message"
                name="message"
                className="input"
                placeholder="Your Message"
            ></textarea>
            </div>
            <button className="btn mt-4">Submit</button>
        </form>
        </div>
    );
}