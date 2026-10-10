package com.demo;

import com.demo.BankAccount;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;

public class BankAccount_getOwner_Test_Path_3 {


    @Test
    public void testGetOwnerCoversReturnStatement() {
        String expectedOwner = "Alice";
        BankAccount account = new BankAccount(expectedOwner, 100.0);

        String actualOwner = account.getOwner();

        assertEquals(expectedOwner, actualOwner);
    }

}
