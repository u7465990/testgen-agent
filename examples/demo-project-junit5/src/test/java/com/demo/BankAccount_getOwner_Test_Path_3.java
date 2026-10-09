package com.demo;

import com.demo.BankAccount;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Assertions;

public class BankAccount_getOwner_Test_Path_3 {


    @Test
    public void testGetOwner() {
        BankAccount account = new BankAccount("Alice", 1000.0);
        String result = account.getOwner();
        Assertions.assertEquals("Alice", result);
    }

}
